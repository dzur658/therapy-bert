import json
import re

import config

from transformers import AutoTokenizer

# 1. Initialize the Fast Tokenizer
# It MUST be the "Fast" version, or the offset mapping will not work.
tokenizer = AutoTokenizer.from_pretrained("answerdotai/ModernBERT-large")

def convert_to_iob(transcript_text, json_entities):
    """
    Takes a raw transcript and a list of entity dictionaries, 
    and returns perfectly aligned BERT tokens and IOB tags.
    """
    # 2. Tokenize the text and extract the character offsets
    tokenized_input = tokenizer(
        transcript_text, 
        return_offsets_mapping=True, 
        truncation=True, 
        max_length=8192 # BERT's maximum context window
    )
    
    input_ids = tokenized_input["input_ids"]
    offsets = tokenized_input["offset_mapping"]
    
    # Initialize an array of "O" tags exactly the length of our tokens
    iob_tags = ["O"] * len(input_ids)
    
    # 3. Find every character span for every entity in the text
    entity_spans = []
    for ent in json_entities:
        text = ent["text"].strip()
        label = ent["label"]
        
        # re.finditer finds ALL occurrences of the phrase, ignoring case
        # re.escape ensures punctuation in the patient's text doesn't break the regex
        for match in re.finditer(re.escape(text), transcript_text, re.IGNORECASE):
            entity_spans.append({
                "start": match.start(),
                "end": match.end(),
                "label": label
            })
            
    # 4. The Intersection Logic: Map the tokens to the spans
    for idx, (token_start, token_end) in enumerate(offsets):
        # Skip special BERT tokens like [CLS] and [SEP] which map to (0, 0)
        if token_start == token_end == 0:
            continue

        # trim BPE artifacts (leading/trailing whitespaces for parsing)
        adjusted_start = token_start
        while adjusted_start < token_end and transcript_text[adjusted_start].isspace():
            adjusted_start += 1
            
        adjusted_end = token_end
        while adjusted_end > adjusted_start and transcript_text[adjusted_end - 1].isspace():
            adjusted_end -= 1
            
        for span in entity_spans:
            # print(span["start"], span["end"])
            # print(adjusted_start, adjusted_end)

            # Does this token's character range fall inside the entity's span?
            if adjusted_start >= span["start"] and adjusted_end <= span["end"]:
                
                # If the previous token is "O" or belongs to a different label, 
                # this MUST be the Beginning (B-) of a new entity.
                if iob_tags[idx-1] == "O" or iob_tags[idx-1].split("-")[-1] != span["label"]:
                    iob_tags[idx] = f"B-{span['label']}"
                else:
                    # Otherwise, we are Inside (I-) an ongoing entity.
                    iob_tags[idx] = f"I-{span['label']}"
                
                # Break out of the inner loop once we've tagged this token
                break 
                
    # Convert token IDs back to readable words just so you can inspect the output
    readable_tokens = tokenizer.convert_ids_to_tokens(input_ids)
    
    return readable_tokens, input_ids, iob_tags

if __name__ == "__main__":
    input_file = config.CLEAN_DATA
    final_dataset = []

    print("Converting Knowledge Graph shards to IOB token arrays...")

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            
            # Only process if the generation was successful
            if data.get('knowledge_graph_shard'):
                transcript = data['knowledge_graph_shard'].get('transcript_text', '') 
                
                # If you didn't save the transcript string directly in the shard, 
                # you will need to reconstruct it from data['conversation'] like in the last script
                if not transcript:
                    from export import format_transcript_to_text
                    from validation import TherapyTranscript
                    convo = TherapyTranscript.model_validate(data['conversation'])
                    transcript = format_transcript_to_text(convo)
                
                entities = data['knowledge_graph_shard']['entities']
                
                # Execute the alignment
                tokens, ids, tags = convert_to_iob(transcript, entities)
                
                # Store the final training package
                final_dataset.append({
                    "tokens": tokens,
                    "ner_tags": tags
                })

    # Save to a format ready for Hugging Face Datasets
    with open(config.OUTPUT_IOB, "w", encoding='utf-8') as f:
        json.dump(final_dataset, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully processed {len(final_dataset)} transcripts into IOB format.")
    print(f"Data saved to {config.OUTPUT_IOB}.")