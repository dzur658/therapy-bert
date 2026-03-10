import torch
from transformers import AutoTokenizer
from modern_bert_ner_trainer import ModernBERT_CRF, UNIQUE_LABELS, id2label, label2id

def load_custom_model(model_dir):
    print(f"Loading custom model from {model_dir}...")
    tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-large")
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    model = ModernBERT_CRF.from_checkpoint(model_dir, map_location=device)
    # Use MPS if available, otherwise CPU
    model.eval()
    model.to(device)

    return tokenizer, model, device

# --- 1. Load the Artifacts ---
MODEL_DIR = "./therapy-modernbert-ner-final"
print(f"Loading custom model from {MODEL_DIR}...")

tokenizer, model, device = load_custom_model(MODEL_DIR)

model.to(device)
model.eval()

# --- 2. The Inference Engine ---
def extract_entities(text):
    print(f"\nAnalyzing: '{text}'")
    
    # Fast tokenization to keep track of word boundaries
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=1024)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    with torch.no_grad():
        # The model's forward pass automatically runs the CRF Viterbi decode when labels=None
        predicted_paths = model.decode(**inputs)
        
    pred_ids = predicted_paths[0]
    predicted_word_tags = [id2label[pred_id] for pred_id in pred_ids]
    
    # --- Reconstruct Words from Subwords ---
    # tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
    entities = []
    current_entity = None
    
    for idx, word_idx in enumerate(predicted_word_tags):
        if word_idx is None:
            continue # Skip [CLS] and [SEP]
            
        tag = id2label[pred_ids[idx]]
        word = tokenizer.decode(inputs["input_ids"][0][idx]).strip()
        
        # We only care about the B- tags to start a new entity string
        if tag.startswith("B-"):
            if current_entity:
                entities.append(current_entity)
            current_entity = {"type": tag[2:], "text": word}
        # If it's an I- tag, append the word to the current entity string
        elif tag.startswith("I-") and current_entity and current_entity["type"] == tag[2:]:
            current_entity["text"] += f" {word}"
        # If it's an O tag, save the current entity and reset
        elif tag == "O":
            if current_entity:
                entities.append(current_entity)
                current_entity = None
                
    if current_entity:
        entities.append(current_entity)
        
    # --- Print Results Cleanly ---
    if not entities:
        print(" -> No clinical entities found.")
    for ent in entities:
        print(f" -> [{ent['type'].upper()}]: {ent['text']}")

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
        extract_entities(sentence)