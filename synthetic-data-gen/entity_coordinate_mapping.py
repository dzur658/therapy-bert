import json
import config

def generate_map(entities_json):
    # 1. Stitch the transcript exactly as the LLM and ModernBERT will see it
    transcript_lines = []
    for turn in entities_json["conversation"]["turns"]:
        transcript_lines.append(f"{turn['speaker']}: {turn['text']}")
    
    full_transcript = "\n\n".join(transcript_lines)
    
    # 2. Get unique entity strings and their labels from Step 1
    unique_entities = {}

    extracted = entities_json.get("extracted_entities") or {}
    entities = extracted.get("entities") or [] 

    for ent in entities:
        if not isinstance(ent, dict):
            continue  # Skip if the entity is not a dictionary (entities are null for this case)

        text = ent.get("text")
        label = ent.get("label")

        # skip empty texts; keep only real strings
        if text is None or text == "":
            continue

        # keep first seen label for a given text (or change behavior if you prefer overwrite)
        unique_entities.setdefault(text, label)
            
    entity_registry = []
    e_id_counter = 0
    
    # 3. Find ALL occurrences of these strings in the transcript
    # If "my daughter" appears 3 times, this captures all 3 as distinct IDs
    for text, label in unique_entities.items():
        search_start = 0
        while True:
            idx = full_transcript.find(text, search_start)
            if idx == -1:
                break # No more occurrences found
            
            entity_registry.append({
                "text": text,
                "label": label,
                "start": idx,
                "end": idx + len(text)
            })
            search_start = idx + len(text)
            
    # 4. Sort the registry chronologically by their appearance in the text
    entity_registry.sort(key=lambda x: x["start"])

    # assign sequential IDs after sorting
    for i, entity in enumerate(entity_registry):
        entity["id"] = f"E{i+1}"

    # wrap the entity map as an object
    entity_map_object = {
        "entities": entity_registry
    }
    
    return entity_map_object, full_transcript

# --- Execution Example ---
# Assuming 'data' is loaded from your JSONL output:
# transcript, registry, injection_string = generate_map(data)
# print(injection_string)

if __name__ == "__main__":
    with open(config.OUTPUT_ENTITIES, "r") as f_in, open(config.OUTPUT_ENTITY_MAP, "w") as f_out:
        for line in f_in:
            entities_json = json.loads(line)
            registry, full_transcript = generate_map(entities_json)
            entities_json["entity_map"] = registry
            entities_json["full_transcript"] = full_transcript
            f_out.write(json.dumps(entities_json) + "\n")