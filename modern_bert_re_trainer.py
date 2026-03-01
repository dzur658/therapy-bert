import numpy as np
import evaluate
from datasets import load_dataset
from typing import get_args
from transformers import (
    AutoTokenizer, 
    AutoModelForSequenceClassification, 
    TrainingArguments, 
    Trainer,
    DataCollatorWithPadding
)

import importlib

# import pydantic validation and config details
validation = importlib.import_module("synthetic-data-gen.validation")
config = importlib.import_module("synthetic-data-gen.config")

# 1. Dynamically Build the Compound Epistemic Labels (SSOT)
predicates = get_args(validation.Relation.model_fields['predicate'].annotation)
proposed_bys = get_args(validation.Relation.model_fields['proposed_by'].annotation)
acceptances = get_args(validation.Relation.model_fields['patient_acceptance'].annotation)

UNIQUE_LABELS = ["NONE"]

for pred in predicates:
    for prop in proposed_bys:
        for acc in acceptances:
            # Enforce our logical rule: Patient proposals are always "Affirmed"
            # if a patient proposes a relation, they are implicitly affirming it
            if prop == "Patient" and acc != "Affirmed":
                continue
            
            compound_label = f"{pred}_{prop}_{acc}"
            UNIQUE_LABELS.append(compound_label)

label2id = {label: i for i, label in enumerate(UNIQUE_LABELS)}
id2label = {i: label for i, label in enumerate(UNIQUE_LABELS)}

print(f"Dynamically generated {len(UNIQUE_LABELS)} unique Relation labels.")

# 2. Model and Tokenizer Initialization
MODEL_NAME = "answerdotai/ModernBERT-large"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
SPECIAL_TOKENS = {"additional_special_tokens": ["[E1]", "[/E1]", "[E2]", "[/E2]"]}
tokenizer.add_special_tokens(SPECIAL_TOKENS)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(UNIQUE_LABELS),
    id2label=id2label,
    label2id=label2id
)

# CRITICAL: Resize the embedding matrix to fit the 4 new special tokens
model.resize_token_embeddings(len(tokenizer))

# 3. Load and Preprocess the Dataset
# (Assuming you already ran prep_re_data.py to create this file)
dataset = load_dataset("json", data_files={
    "train": config.RE_TRAINING_DATA_DIR + "/train.jsonl",
    "validation": config.RE_TRAINING_DATA_DIR + "/val.jsonl",
    "test": config.RE_TRAINING_DATA_DIR + "/test.jsonl"
}, split="train")

def preprocess_function(examples):
    # ModernBERT handles the max_length of 8192 natively, but we truncate to 1024 
    # here to save VRAM since most single therapy transcripts won't exceed that.
    tokenized = tokenizer(examples["text"], truncation=True, max_length=1024)
    tokenized["labels"] = [label2id[label] for label in examples["label"]]
    return tokenized

tokenized_datasets = dataset.map(preprocess_function, batched=True)

# Data collator dynamically pads batches to the longest sequence in that specific batch
data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

# 4. Evaluation Metrics
accuracy_metric = evaluate.load("accuracy")
f1_metric = evaluate.load("f1")

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    
    # Using macro F1 because we have many complex classes and want to penalize 
    # the model if it ignores minority classes (like "Realized_Later")
    # this is done to equalize out the heavy bias towards "NONE" that naturally occurs in RE datasets
    acc = accuracy_metric.compute(predictions=predictions, references=labels)["accuracy"]
    f1 = f1_metric.compute(predictions=predictions, references=labels, average="macro")["f1"]
    
    return {"accuracy": acc, "f1_macro": f1}

# 5. Training Configuration
training_args = TrainingArguments(
    output_dir="./therapy-modernbert-re",
    eval_strategy="epoch",  # Note: evaluation_strategy is deprecated in newer transformers
    save_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=8,
    per_device_eval_batch_size=8,
    num_train_epochs=3,
    weight_decay=0.01,
    bf16=True, # ModernBERT is highly optimized for bfloat16
    load_best_model_at_end=True,
    metric_for_best_model="f1_macro",
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["test"],
    tokenizer=tokenizer,
    data_collator=data_collator,
    compute_metrics=compute_metrics,
)

if __name__ == "__main__":
    print("Initializing Relation Extraction Training...")
    trainer.train()
    
    trainer.save_model("./therapy-modernbert-re-final")
    print("Training Complete! Sequence Classifier saved to ./therapy-modernbert-re-final")