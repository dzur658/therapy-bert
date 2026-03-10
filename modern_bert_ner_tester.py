import json
import os

import torch
from transformers import AutoTokenizer

import importlib
from typing import get_args

config = importlib.import_module("synthetic-data-gen.config")
validation = importlib.import_module("synthetic-data-gen.validation")

from ner_crf_layer import ModernBERT_CRF

# 1. Recreate the Label Maps (Must match your training script exactly)
# 1. Define the exact vocabulary of your Knowledge Graph
Entity = validation.Entity

base_labels = get_args(Entity.model_fields['label'].annotation)

# 2. Dynamically construct the IOB array
UNIQUE_LABELS = ["O"]
for label in base_labels:
    UNIQUE_LABELS.append(f"B-{label}")
    UNIQUE_LABELS.append(f"I-{label}")

label2id = {label: i for i, label in enumerate(UNIQUE_LABELS)}
id2label = {i: label for i, label in enumerate(UNIQUE_LABELS)}

def load_custom_model(model_dir):
    print(f"Loading custom model from {model_dir}...")
    tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-large")
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = ModernBERT_CRF.from_checkpoint(model_dir, map_location=device)
    # Use MPS if available, otherwise CPU
    model.eval()
    model.to(device)

    return tokenizer, model, device

def analyze_predictions(tokenizer, model, device, tokens, true_tags):
    input_ids = tokenizer.convert_tokens_to_ids(tokens)
    inputs = {
        "input_ids": torch.tensor([input_ids], dtype=torch.long, device=device),
        "attention_mask": torch.ones((1, len(input_ids)), dtype=torch.long, device=device),
    }

    with torch.no_grad():
        predicted_paths = model.decode(**inputs)

    # Extract the first (and only) path in the batch
    pred_ids = predicted_paths[0]
    predicted_word_tags = [id2label[pred_id] for pred_id in pred_ids]

    # Print Side-by-Side Comparison
    print(f"\n{'-'*70}")
    print(f"{'TOKEN':<20} | {'TRUE TAG':<20} | {'PREDICTED TAG':<20}")
    print(f"{'-'*70}")
    
    for token, true_tag, pred_tag in zip(tokens, true_tags, predicted_word_tags):
        # Highlight mismatches with a terminal marker (***)
        marker = " " if true_tag == pred_tag else "***"
        
        # Only print rows that aren't just 'O' matching 'O' to avoid terminal spam
        if true_tag != "O" or pred_tag != "O":
            print(f"{token:<20} | {true_tag:<20} | {pred_tag:<20} {marker}")

if __name__ == "__main__":
    MODEL_DIR = "./therapy-bert-ner-phase2/checkpoint-3792"
    TEST_FILE = os.path.join(config.MAP_DIR, "val.jsonl")
    
    tokenizer, model, device = load_custom_model(MODEL_DIR)
    
    print("\nRunning Forensic Evaluation on Test Samples...")
    
    # Just grab the first 3 examples from the test set to analyze
    with open(TEST_FILE, 'r') as f:
        for i, line in enumerate(f):
            if i >= 3: 
                break
            record = json.loads(line)
            tokens = record["tokens"]
            true_tags = record["ner_tags"]
            
            analyze_predictions(tokenizer, model, device, tokens, true_tags)