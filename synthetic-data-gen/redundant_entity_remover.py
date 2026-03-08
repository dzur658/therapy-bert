import json
import config

def clean_clinical_jsonl(input_filepath, output_filepath):
    total_processed = 0
    records_kept = 0
    records_dropped = 0

    print(f"Starting cleanup of {input_filepath}...")

    # Open both files simultaneously to stream the data
    with open(input_filepath, 'r', encoding='utf-8') as infile, \
         open(output_filepath, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            if not line.strip():
                continue
                
            total_processed += 1
            record = json.loads(line)
            
            # STEP 1: Check if the record actually has entity data
            shard = record.get("knowledge_graph_shard") or {}
            entities = shard.get("entities") or []
            
            if len(entities) == 0:
                records_dropped += 1
                continue  # Skip to the next line without writing
                
            # STEP 2: Delete the redundant keys
            # .pop(key, None) safely removes the key if it exists, or does nothing if it doesn't
            record.pop("extracted_entities", None)
            record.pop("entity_map", None)
            
            # STEP 3: Write the cleaned, streamlined JSON string to the new file
            outfile.write(json.dumps(record) + '\n')
            records_kept += 1

    print("\n--- Data Pipeline Cleanup Complete ---")
    print(f"Total records scanned: {total_processed}")
    print(f"Records kept (valid entities): {records_kept}")
    print(f"Records dropped (empty/missing): {records_dropped}")
    print(f"Cleaned dataset saved to: {output_filepath}")

if __name__ == "__main__":
    # Change these filenames to match your local setup
    INPUT_FILE = config.OUTPUT_SHARDS
    OUTPUT_FILE = config.CLEAN_DATA
    
    clean_clinical_jsonl(INPUT_FILE, OUTPUT_FILE)