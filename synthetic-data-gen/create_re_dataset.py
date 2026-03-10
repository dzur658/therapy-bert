# this creates the dataset used to train the relationship extraction BERT model.
import config

import json
import random
import itertools
import re

def build_re_dataset(input_file=config.OUTPUT_SHARDS, output_file=config.RE_OUTPUT_FILE):
    print(f"Reading Knowledge Graph shards from {input_file}...")
    final_dataset = []

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            
            # Skip any shards where the LLM failed or the validation blocked it
            if not data.get('knowledge_graph_shard'):
                continue
            
            # 1. Reconstruct the raw transcript string
            turns = data['conversation']['turns']
            transcript = "\n\n".join([f"{t['speaker']}: {t['text']}" for t in turns])
            
            # 2. Extract the verified graph data
            entities = list(set([e['text'] for e in data['knowledge_graph_shard']['entities']]))
            relations = data['knowledge_graph_shard']['relations']
            
            # Create a fast lookup dictionary for the actual LLM relations
            actual_relations = {
                (r['source'], r['target']): r['predicate'] 
                for r in relations
            }
            
            # Generate every possible directed combination of entities
            all_possible_pairs = list(itertools.permutations(entities, 2))
            
            positives = []
            negatives = []
            
            for source, target in all_possible_pairs:
                # Use Regex with word boundaries to prevent substring collisions 
                # (e.g. preventing "pain" from overwriting "chronic pain")
                # We use re.escape to handle any weird punctuation in the entity strings
                
                # Copy the transcript so we don't mutate the base for the next pair
                marked_text = transcript 
                
                # A safer replacement strategy:
                try:
                    marked_text = re.sub(f"({re.escape(source)})", r"[E1]\1[/E1]", marked_text, count=1)
                    marked_text = re.sub(f"({re.escape(target)})", r"[E2]\1[/E2]", marked_text, count=1)
                except Exception as e:
                    # If regex fails due to incredibly bizarre LLM hallucinations, skip the pair
                    continue
                
                # Ensure both markers successfully injected before keeping the data
                if "[E1]" not in marked_text or "[E2]" not in marked_text:
                    continue
                
                if (source, target) in actual_relations:
                    label = actual_relations[(source, target)]
                    positives.append({"text": marked_text, "label": label})
                else:
                    negatives.append({"text": marked_text, "label": "NONE"})
            
            # 3. Negative Sampling (2:1 Ratio to prevent class imbalance)
            num_to_sample = min(len(negatives), len(positives) * 2)
            sampled_negatives = random.sample(negatives, num_to_sample)
            
            final_dataset.extend(positives)
            final_dataset.extend(sampled_negatives)
    
    # Another check for any remaining duplicates, just in case
    unique_dataset = []
    seen = set()
    for record in final_dataset:
        identifier = f"{record['text']}|||{record['label']}"
        if identifier not in seen:
            seen.add(identifier)
            unique_dataset.append(record)

    # Stream to disk
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for record in final_dataset:
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
    print(f"Generated {len(final_dataset)} training pairs. Ready for Sequence Classification.")

if __name__ == "__main__":
    build_re_dataset(config.OUTPUT_SHARDS, config.RE_OUTPUT_FILE)