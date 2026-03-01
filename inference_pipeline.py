import itertools
from transformers import pipeline, AutoTokenizer

class TherapyGraphExtractor:
    def __init__(self, ner_model_path, re_model_path):
        print("Loading ModernBERT Models into memory...")
        
        # 1. Load the CSI (NER Model)
        # aggregation_strategy="simple" automatically merges B- and I- tags back into full words!
        self.ner_pipeline = pipeline(
            "token-classification", 
            model=ner_model_path, 
            aggregation_strategy="simple",
            device=0 # Set to -1 if running on CPU
        )
        
        # 2. Load the Lead Detective (RE Model)
        self.re_pipeline = pipeline(
            "text-classification", 
            model=re_model_path,
            device=0,
            top_k=1 # Only return the highest probability label
        )
        self.re_tokenizer = AutoTokenizer.from_pretrained(re_model_path)

    def chunk_transcript(self, text, max_words=3000, overlap_turns=4):
        """
        Slices the Whisper transcript into overlapping chunks to fit in VRAM reasonably,
        ensuring we strictly break on the \n\n boundaries.
        """
        turns = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        for _, turn in enumerate(turns):
            turn_words = len(turn.split())
            
            # If adding this turn blows our limit, save the chunk and backtrack
            if current_word_count + turn_words > max_words and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                
                # Backtrack to create the overlap (e.g., grab the last 4 turns)
                overlap_start = max(0, len(current_chunk) - overlap_turns)
                current_chunk = current_chunk[overlap_start:]
                current_word_count = sum(len(t.split()) for t in current_chunk)
                
            current_chunk.append(turn)
            current_word_count += turn_words
            
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
        return chunks

    def process_transcript(self, raw_text):
        print("Chunking transcript...")
        chunks = self.chunk_transcript(raw_text)
        
        master_entities = {} # Use dict to deduplicate by text
        master_relations = set() # Use set to deduplicate edges
        
        for chunk_idx, chunk_text in enumerate(chunks):
            print(f"Processing Chunk {chunk_idx + 1}/{len(chunks)}...")
            
            # --- STEP 1: EXTRACT NODES (NER) ---
            # The pipeline returns: [{'entity_group': 'Symptom', 'word': 'panic attacks', ...}]
            ner_results = self.ner_pipeline(chunk_text)
            
            chunk_entities = []
            for ent in ner_results:
                clean_text = ent['word'].strip()
                label = ent['entity_group']
                master_entities[clean_text] = label
                chunk_entities.append(clean_text)
                
            # Deduplicate entities within this specific chunk for pairing
            chunk_entities = list(set(chunk_entities))
            
            # --- STEP 2: BUILD THE PAIRS ---
            all_possible_pairs = list(itertools.permutations(chunk_entities, 2))
            
            re_inputs = []
            pair_mappings = []
            
            for source, target in all_possible_pairs:
                # Inject the [E1] and [E2] spotlights
                marked_text = chunk_text.replace(source, f"[E1]{source}[/E1]", 1)
                marked_text = marked_text.replace(target, f"[E2]{target}[/E2]", 1)
                
                # We truncate here just in case a chunk got slightly too large
                re_inputs.append(marked_text[:4000]) 
                pair_mappings.append((source, target))
                
            if not re_inputs:
                continue

            # --- STEP 3: EXTRACT EDGES (RE) ---
            re_results = self.re_pipeline(re_inputs, batch_size=8, truncation=True, max_length=1024)
            
            # --- STEP 4: PARSE EPISTEMIC LABELS ---
            for (source, target), result in zip(pair_mappings, re_results):
                label = result[0]['label']
                
                if label == "NONE":
                    continue
                    
                # Split our compound label back into its Pydantic fields
                # e.g., "CAUSES_Patient_Affirmed" -> ["CAUSES", "Patient", "Affirmed"]
                parts = label.split("_", 2) 
                predicate = parts[0]
                proposed_by = parts[1]
                acceptance = parts[2] if len(parts) > 2 else "N/A"
                
                # Add to master set as a tuple to automatically deduplicate overlaps
                master_relations.add((source, predicate, target, proposed_by, acceptance))

        # --- STEP 5: ASSEMBLE FINAL JSON ---
        final_graph = {
            "entities": [{"text": text, "label": label} for text, label in master_entities.items()],
            "relations": [
                {
                    "source": r[0],
                    "predicate": r[1],
                    "target": r[2],
                    "proposed_by": r[3],
                    "patient_acceptance": r[4]
                } for r in master_relations
            ]
        }
        
        return final_graph

# ==========================================
# Example Usage
# ==========================================
if __name__ == "__main__":
    extractor = TherapyGraphExtractor(
        ner_model_path="./therapy-modernbert-ner-final",
        re_model_path="./therapy-modernbert-re-final"
    )
    
    with open("sample_whisper_transcript.txt", "r") as f:
        whisper_text = f.read()
        
    knowledge_graph = extractor.process_transcript(whisper_text)
    
    import json
    print(json.dumps(knowledge_graph, indent=2))