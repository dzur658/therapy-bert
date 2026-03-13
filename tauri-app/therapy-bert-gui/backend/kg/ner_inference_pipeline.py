import torch
import os
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer
from ner_crf_layer import ModernBERT_CRF

def _resolve_model_source(model_source):
    if os.path.isdir(model_source):
        return model_source

    if os.path.isfile(model_source):
        raise ValueError(f"Expected a model directory or HF repo ID, got file path: {model_source}")

    print(f"Resolving Hugging Face snapshot for {model_source}...")
    return snapshot_download(repo_id=model_source)

def load_custom_model(model_dir):
    resolved_model_dir = _resolve_model_source(model_dir)
    print(f"Loading custom model from {resolved_model_dir}...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(resolved_model_dir)
    except OSError:
        tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-large")

    if torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("mps") if torch.backends.mps.is_available() else torch.device("cpu")

    model = ModernBERT_CRF.from_checkpoint(resolved_model_dir, map_location=device)
    # Use MPS if available, otherwise CPU
    model.eval()
    model.to(device)

    return tokenizer, model, device

# --- 1. Load the Artifacts ---
# MODEL_DIR = "./therapy-modernbert-ner-final"
# print(f"Loading custom model from {MODEL_DIR}...")

# tokenizer, model, device = load_custom_model(MODEL_DIR)

# model.to(device)
# model.eval()

# --- 2. The Inference Engine ---
def extract_entities(text, tokenizer, model, device):
    print(f"\nAnalyzing: '{text}'")
    
    # Tokenization
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=8192)
    inputs_to_device = {k: v.to(device) for k, v in inputs.items()}
    
    with torch.no_grad():
        # The model's forward pass automatically runs the CRF Viterbi decode
        predicted_paths = model.decode(**inputs_to_device)
        
    pred_ids = predicted_paths[0]
    input_ids = inputs["input_ids"][0].tolist() # Extract the raw integers
    
    entities = []
    current_entity = None
    
    for idx, tag_id in enumerate(pred_ids):
        token_id = input_ids[idx]
        
        # PROPERLY skip special tokens ([CLS], [SEP], [PAD])
        if token_id in tokenizer.all_special_ids:
            continue
            
        tag = model.id2label[tag_id]
        
        # If it's a B- tag, start a new entity
        if tag.startswith("B-"):
            if current_entity:
                # Decode the accumulated token IDs all at once!
                current_entity["text"] = tokenizer.decode(current_entity["token_ids"]).strip()
                del current_entity["token_ids"] # Clean up the dictionary
                entities.append(current_entity)
            
            # Store the raw ID, not the string
            current_entity = {"type": tag[2:], "token_ids": [token_id]}
            
        # If it's an I- tag, append the raw ID to the array
        elif tag.startswith("I-") and current_entity and current_entity["type"] == tag[2:]:
            current_entity["token_ids"].append(token_id)
            
        # If it's an O tag, finalize the current entity
        elif tag == "O":
            if current_entity:
                current_entity["text"] = tokenizer.decode(current_entity["token_ids"]).strip()
                del current_entity["token_ids"]
                entities.append(current_entity)
                current_entity = None
                
    # Catch the edge case where the sequence ends exactly on an entity
    if current_entity:
        current_entity["text"] = tokenizer.decode(current_entity["token_ids"]).strip()
        del current_entity["token_ids"]
        entities.append(current_entity)
        
    if not entities:
        return {"entities": []}

    return {"entities": entities}

# --- 3. Test It ---
if __name__ == "__main__":
    test_sentences = [
        "My anxiety has been through the roof since my ex-husband called me.",
        "I couldn't sleep at all last night, my chest feels incredibly tight.",
        "To cope with the stress, I usually isolate myself in my room for hours.",
        "The flashing lights from the ambulance triggered a massive panic attack."
    ]
    
    print("\nStarting Clinical Entity Extraction Engine...")
    for sentence in test_sentences:
        result = extract_entities(sentence)
        print(f"Text: {sentence}")
        for entity in result["entities"]:
            print(f" -> [{entity['type'].upper()}]: {entity['text']}")