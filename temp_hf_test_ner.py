import torch
from transformers import AutoTokenizer

# this is the example from the model card on huggingface

# Contains the custom Condtional Random Field head
from ner_crf_layer import ModernBERT_CRF

# get original ModernBERT Large Tokenizer
tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-large")

# your accelerator
device = "cuda"

# load model using the from checkpoint function
model = ModernBERT_CRF.from_checkpoint("[REPLACE ME WITH PATH TO REPO]", map_location=device)

model.eval()
model.to(device)

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

text_to_analyze = "My anxiety has been through the roof since my ex-husband called me."

entities_obj = extract_entities(text_to_analyze, tokenizer, model, device)
print(entities_obj)
