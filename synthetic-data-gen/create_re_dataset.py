# this creates the dataset used to train the relationship extraction BERT model.
import config

import json
import random
import itertools

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
            entities = [e['text'] for e in data['knowledge_graph_shard']['entities']]
            relations = data['knowledge_graph_shard']['relations']
            
            # Create a fast lookup dictionary for the actual LLM relations
            actual_relations = {(r['source'], r['target']): r['predicate'] for r in relations}
            
            # Generate every possible directed combination of entities
            all_possible_pairs = list(itertools.permutations(entities, 2))
            
            positives = []
            negatives = []
            
            for source, target in all_possible_pairs:
                # Insert the Entity Markers into the text
                marked_text = transcript.replace(source, f"[E1]{source}[/E1]", 1)
                marked_text = marked_text.replace(target, f"[E2]{target}[/E2]", 1)
                
                # Categorize as Positive or Negative
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

    # Stream to disk
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for record in final_dataset:
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            
    print(f"Generated {len(final_dataset)} training pairs. Ready for Sequence Classification.")

if __name__ == "__main__":
    build_re_dataset("./datasets/gemini-tests/gemini_shards.jsonl")