import importlib

config = importlib.import_module("synthetic-data-gen.config")
validation = importlib.import_module("synthetic-data-gen.validation")

from ner_crf_layer import ModernBERT_CRF

import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer, 
    TrainingArguments, 
    Trainer, 
    DataCollatorForTokenClassification,
    EarlyStoppingCallback
)

import json as js
import evaluate
import numpy as np
from typing import get_args
import platform
import os

# for older macOS versions, we do not want to use bfloat16 as it is only supported in MacOS 14+
is_macos_14_plus = (
    platform.system() == "Darwin"
    and int(platform.mac_ver()[0].split(".")[0]) >= 14
)

use_mps_bf16 = torch.backends.mps.is_available() and is_macos_14_plus
use_cuda_bf16 = torch.cuda.is_available()

# check for MPS
print(torch.backends.mps.is_available())

# 1. Define the exact vocabulary of your Knowledge Graph
Entity = validation.Entity

base_labels = get_args(Entity.model_fields['label'].annotation)

# 2. Dynamically construct the IOB array
UNIQUE_LABELS = ["O"]
for label in base_labels:
    UNIQUE_LABELS.append(f"B-{label}")
    UNIQUE_LABELS.append(f"I-{label}")

# Create dictionaries to translate between human strings and computer integers
label2id = {label: i for i, label in enumerate(UNIQUE_LABELS)}
id2label = {i: label for i, label in enumerate(UNIQUE_LABELS)}

# 2. Load the Tokenizer and Model
MODEL_NAME = "answerdotai/ModernBERT-large"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# We use AutoModelForTokenClassification and pass it our custom label maps
model = ModernBERT_CRF(
    model_name=MODEL_NAME,
    num_labels=len(UNIQUE_LABELS),
    id2label=id2label,
    label2id=label2id
)

# 3. Load and Preprocess the Dataset
dataset = load_dataset("json", data_files={"train": config.MAP_DIR + "/train.jsonl",
                                            "validation": config.MAP_DIR + "/val.jsonl",
                                            "test": config.MAP_DIR + "/test.jsonl"
                                            })

class CRFTrainer(Trainer):
    def _save(self, output_dir=None, state_dict=None):
        output_dir = output_dir or self.args.output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.model.save_checkpoint(output_dir)

        processor = getattr(self, "processing_class", None)
        if processor is None:
            processor = getattr(self, "tokenizer", None)

        if processor is not None:
            processor.save_pretrained(output_dir)

        # dump training arguments in a json structure
        with open(os.path.join(output_dir, "training_args.json"), "w", encoding="utf-8") as handle:
            js.dump(self.args.to_dict(), handle, indent=2)

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        # We can just let our custom forward() method handle the loss calculation natively.
        outputs = model(**inputs)
        loss = outputs["loss"]
        return (loss, outputs) if return_outputs else loss

    def prediction_step(self, model, inputs, prediction_loss_only, ignore_keys=None):
        with torch.no_grad():
            inputs = self._prepare_inputs(inputs)

            output = model(**inputs)
            
            # Get the loss and emission logits
            loss = output["loss"]
            logits = output["logits"]
            
            if prediction_loss_only:
                return (loss, None, None)
                
            # Run Viterbi decoding to get the exact tag paths
            bool_mask = inputs["attention_mask"].type(torch.bool)
            predicted_paths = model.crf.decode(logits, mask=bool_mask)
            
            # Pad the variable-length Viterbi lists back into a perfect rectangle 
            # so the Hugging Face evaluation loop doesn't crash
            max_len = logits.shape[1]
            padded_preds = []
            for path in predicted_paths:
                padded_path = path + [-100] * (max_len - len(path))
                padded_preds.append(padded_path)
                
            predictions_tensor = torch.tensor(padded_preds, device=logits.device)
            labels = inputs.get("labels")

        return (loss, predictions_tensor, labels)

def preprocess_function(examples):
    batch_input_ids = []
    batch_attention_mask = []
    batch_labels = []

    for tokens, tags in zip(examples["tokens"], examples["ner_tags"]):
        if len(tokens) != len(tags):
            raise ValueError("Tokens and NER tags must be the same length.")

        input_ids = tokenizer.convert_tokens_to_ids(tokens)
        attention_mask = [1] * len(input_ids)
        labels = [label2id[tag] for tag in tags]

        batch_input_ids.append(input_ids)
        batch_attention_mask.append(attention_mask)
        batch_labels.append(labels)

    return {
        "input_ids": batch_input_ids,
        "attention_mask": batch_attention_mask,
        "labels": batch_labels,
    }

metric = evaluate.load("seqeval")

def compute_metrics(eval_pred):
    """
    Takes the model's raw logits and the true labels, strips out the padding,
    and calculates exact-match span scores.
    """
    predictions = eval_pred.predictions
    labels = eval_pred.label_ids

    if isinstance(predictions, tuple):
        predictions = predictions[0]
    
    predictions = np.asarray(predictions)
    labels = np.asarray(labels)

    # get predictions and labels (special tokens are included in these)
    true_predictions = [
        [id2label[p] for p, l in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]
    
    true_labels = [
        [id2label[l] for p, l in zip(prediction, label) if l != -100]
        for prediction, label in zip(predictions, labels)
    ]

    # Compute the metrics using the seqeval library
    results = metric.compute(predictions=true_predictions, references=true_labels)
    return {
        "precision": results["overall_precision"],
        "recall": results["overall_recall"],
        "f1": results["overall_f1"],
        "accuracy": results["overall_accuracy"],
    }

# Apply the preprocessing map and drop the old string columns
tokenized_datasets = dataset.map(
    preprocess_function, 
    batched=True, 
    remove_columns=["tokens", "ner_tags"]
)

# 4. The Data Collator
# This automatically pads your transcripts with 0s so they are all the same length in a batch,
# and it smartly pads your labels with -100 so the model doesn't train on the padding!
data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)

# 5. Define Training Arguments
phase1_args = TrainingArguments(
    output_dir="./therapy-bert-ner-phase1",
    eval_strategy="epoch",      # Check performance at the end of each epoch
    learning_rate=1e-3,               # Aggressive lr for the randomly initialized CRF head to stabilize quickly
    per_device_train_batch_size=4,    # Adjust down to 4 or 2 if your GPU runs out of memory
    per_device_eval_batch_size=8,
    num_train_epochs=1,               # 3 to 5 epochs is usually the sweet spot for NER
    weight_decay=0.01,
    bf16=use_cuda_bf16 or use_mps_bf16,                        # ModernBERT loves bfloat16 precision for faster training
    logging_steps=50,
    dataloader_num_workers=4,              # Use multiple CPU cores to speed up data loading
    train_sampling_strategy="group_by_length",              # Group sequences of similar length together for efficiency
    save_strategy="epoch",            # Save a model checkpoint every epoch
)

# 6. Initialize and Launch the Trainer
phase1_trainer = CRFTrainer(
    model=model,
    args=phase1_args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["validation"],
    data_collator=data_collator,
    compute_metrics=compute_metrics,
)

phase2_args = TrainingArguments(
    output_dir="./therapy-bert-ner-phase2",
    eval_strategy="epoch",      # Check performance at the end of each epoch
    learning_rate=2e-6,               # small learning rate to keep modernbert weights from diverging too much during fine-tuning
    per_device_train_batch_size=4,    # Adjust down to 4 or 2 if your GPU runs out of memory
    per_device_eval_batch_size=8,
    num_train_epochs=10,               # Early stopping run until eval loss starts spiking
    weight_decay=0.01,
    bf16=use_cuda_bf16 or use_mps_bf16,                        # ModernBERT loves bfloat16 precision for faster training
    logging_steps=50,
    dataloader_num_workers=4,              # Use multiple CPU cores to speed up data loading
    train_sampling_strategy="group_by_length",              # Group sequences of similar length together for efficiency
    save_strategy="epoch",            # Save a model checkpoint every epoch
    metric_for_best_model="eval_loss",        # eval loss for best model selection, since seqeval metrics can be noisy in early stages of training
    greater_is_better=False,                # lower eval loss is better
    load_best_model_at_end=True,          # Automatically load the best model when finished training
)

# 6. Initialize and Launch the Trainer
phase2_trainer = CRFTrainer(
    model=model,
    args=phase2_args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["validation"],
    data_collator=data_collator,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
)

print(f"trainer device: {phase1_args.device}")
print(f"cuda available: {torch.cuda.is_available()}")
print(f"mps available: {torch.backends.mps.is_available()}")
print(f"bf16 enabled: {phase1_args.bf16}")

if __name__ == "__main__":
    print("Initializing ModernBERT-large training...")

    # freeze ModernBERT to prevent system shock from bolting on the CRF head with random weights
    print("\n--- PHASE 1: Training the CRF Head (Backbone Frozen) ---")
    for param in model.bert.parameters():
        param.requires_grad = False

    # Train for just 3 epoch to stabilize the random weights
    phase1_trainer.train()
    
    # Thaw modernbert
    print("\n--- PHASE 2: Fine-Tuning Entire Model (ModernBERT Thawed) ---")
    for param in model.bert.parameters():
        param.requires_grad = True
    
    # Continue training seamlessly
    phase2_trainer.train()
    
    # Save the final pristine model to your hard drive
    phase2_trainer.save_model("./therapy-modernbert-ner-final")
    tokenizer.save_pretrained("./therapy-modernbert-ner-final")
    print("Training complete! Model saved to ./therapy-modernbert-ner-final")