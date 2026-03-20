import numpy as np
import torch
import evaluate
from datasets import load_dataset
from typing import get_args
from transformers import (
    AutoTokenizer, 
    TrainingArguments, 
    Trainer,
    DataCollatorWithPadding,
    EarlyStoppingCallback
)

import platform
import importlib
import os
import json

from modern_bert_re_layers import ModernBERT_Entity_Pooling_RE

# truncate to maximum context window ModernBERT supports 8192 tokens
MAX_RE_TOKENS = 8192

# for older macOS versions, we do not want to use bfloat16 as it is only supported in MacOS 14+
is_macos_14_plus = (
    platform.system() == "Darwin"
    and int(platform.mac_ver()[0].split(".")[0]) >= 14
)

use_mps_bf16 = torch.backends.mps.is_available() and is_macos_14_plus
use_cuda_bf16 = torch.cuda.is_available()

# 1. Setup Data & Labels (Same as your script)
# 1. Setup Data & Labels
validation = importlib.import_module("synthetic-data-gen.validation")
config = importlib.import_module("synthetic-data-gen.config")

# We only care about the base predicate now
predicates = get_args(validation.Relation.model_fields['predicate'].annotation)

UNIQUE_LABELS = ["NONE"] + list(predicates)

label2id = {label: i for i, label in enumerate(UNIQUE_LABELS)}
id2label = {i: label for i, label in enumerate(UNIQUE_LABELS)}

print(f"Streamlined classification space: {len(UNIQUE_LABELS)} unique relation labels.")

# 2. Tokenizer & Vocabulary
MODEL_NAME = "answerdotai/ModernBERT-large"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
SPECIAL_TOKENS = {"additional_special_tokens": ["[E1]", "[/E1]", "[E2]", "[/E2]"]}
tokenizer.add_special_tokens(SPECIAL_TOKENS)

# 3. Data Preprocessing
dataset = load_dataset("json", data_files={
    "train": "./synthetic-data-gen/" + config.RE_SPLIT_DATA_DIR + "/train.jsonl",
    "validation": "./synthetic-data-gen/" + config.RE_SPLIT_DATA_DIR + "/val.jsonl"
})

e1_token_id = tokenizer.convert_tokens_to_ids("[E1]")
e2_token_id = tokenizer.convert_tokens_to_ids("[E2]")

def preprocess_function(examples):
    tokenized = tokenizer(examples["text"])
    
    filtered = {
        "input_ids": [],
        "attention_mask": [],
        "labels": []
    }

    for input_ids, attention_mask, label in zip(
        tokenized["input_ids"],
        tokenized["attention_mask"],
        examples["label"]
    ):
        if e1_token_id not in input_ids or e2_token_id not in input_ids:
            # skip if for some reason there's no entities
            continue

        if len(input_ids) > MAX_RE_TOKENS:
            # skip examples that exceed the model's maximum context window
            continue

        filtered["input_ids"].append(input_ids)
        filtered["attention_mask"].append(attention_mask)
        filtered["labels"].append(label2id[label])

    return filtered

tokenized_datasets = dataset.map(preprocess_function, batched=True, remove_columns=["text", "label"])
data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

# 4. Metrics
accuracy_metric = evaluate.load("accuracy")
f1_metric = evaluate.load("f1")

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    acc = accuracy_metric.compute(predictions=predictions, references=labels)["accuracy"]
    f1 = f1_metric.compute(predictions=predictions, references=labels, average="macro")["f1"]
    return {"accuracy": acc, "f1_macro": f1}

# 5. Custom Trainer to handle Dict outputs
class RETrainer(Trainer):
    def _save(self, output_dir=None, state_dict=None):
        output_dir = output_dir or self.args.output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.model.save_checkpoint(output_dir)

        processor = getattr(self, "processing_class", None)
        if processor is None:
            processor = getattr(self, "tokenizer", None)

        if processor is not None:
            processor.save_pretrained(output_dir)

        with open(os.path.join(output_dir, "training_args.json"), "w", encoding="utf-8") as handle:
            json.dump(self.args.to_dict(), handle, indent=2)

if __name__ == "__main__":
    print("\nInitializing ModernBERT SOTA Relation Extraction...")
    model = ModernBERT_Entity_Pooling_RE(MODEL_NAME, 
                                         len(UNIQUE_LABELS), 
                                         tokenizer,
                                         label2id=label2id,
                                         id2label=id2label
                                         )
    
    if torch.cuda.is_available():
        device = torch.device("cuda")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
    else:
        device = torch.device("cpu")

    model.to(device)

    # ==========================================
    # PHASE 1: FREEZE BRAIN, THAW DICTIONARY
    # ==========================================
    print("\n--- PHASE 1: Training Entity Markers & Classifier (Backbone Frozen) ---")
    for name, param in model.bert.named_parameters():
        # Keep embeddings thawed so the 4 new special tokens can learn
        if "embeddings" in name:
            param.requires_grad = True
        else:
            param.requires_grad = False
            
    training_args_phase1 = TrainingArguments(
        output_dir="./therapy-re-phase1",
        eval_strategy="epoch",
        learning_rate=1e-3, # Sledgehammer for new token embeddings
        per_device_train_batch_size=2,
        per_device_eval_batch_size=1,
        num_train_epochs=1,
        weight_decay=0.01,
        bf16=use_cuda_bf16 or use_mps_bf16,
        train_sampling_strategy="group_by_length",
        logging_steps=50,
        gradient_accumulation_steps=8,
        dataloader_num_workers=2,
        save_strategy="no"
    )
    
    trainer_phase1 = RETrainer(
        model=model,
        args=training_args_phase1,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["validation"],
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )
    trainer_phase1.train()

    # ==========================================
    # PHASE 2: THAW EVERYTHING & FINE TUNE
    # ==========================================
    print("\n--- PHASE 2: Fine-Tuning Entire Model (Backbone Thawed) ---")
    for param in model.bert.parameters():
        param.requires_grad = True
        
    training_args_phase2 = TrainingArguments(
        output_dir="./therapy-modernbert-re-final",
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5, # Back to scalpel for full network
        per_device_train_batch_size=2,
        per_device_eval_batch_size=1,
        num_train_epochs=10, 
        weight_decay=0.01,
        bf16=use_cuda_bf16 or use_mps_bf16,
        logging_steps=50,
        gradient_accumulation_steps=8,
        dataloader_num_workers=2,
        train_sampling_strategy="group_by_length",
        metric_for_best_model="f1_macro",
        greater_is_better=True,
        load_best_model_at_end=True,
    )
    
    trainer_phase2 = RETrainer(
        model=model,
        args=training_args_phase2,
        train_dataset=tokenized_datasets["train"],
        eval_dataset=tokenized_datasets["validation"],
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)]
    )
    trainer_phase2.train()
    
    trainer_phase2.save_model("./therapy-modernbert-re-final")
    tokenizer.save_pretrained("./therapy-modernbert-re-final")
    print("\nTraining Complete! State-of-the-Art RE Model saved.")