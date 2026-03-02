import litellm
from export import format_transcript_to_text
from validation import TherapyTranscript, EntityExtraction, contains_mandarin
import config
import judge

import json
from tqdm import tqdm

SYSTEM_PROMPT = """\
You are an expert clinical data extractor. Your job is to read a therapy transcript and extract ONLY the clinical entities.
You must extract the exact, messy phrasing used by the patient or therapist as the entity "text", and strictly categorize them using only the approved Labels.

ENTITY LABELING DEFINITIONS & STRICT GUARDRAILS:

1. Symptom
- Definition: A physical, cognitive, or behavioral manifestation of a psychological state or medical condition.
- Examples: "heart palpitations", "my hands shake", "couldn't sleep", "panic attack".
- Constraint: This must be an involuntary reaction or a specific clinical sign. Do not confuse this with an Emotion.

2. Emotion
- Definition: A direct, internal feeling state expressed by the patient. 
- Examples: "angry", "sad", "guilty", "overwhelmed".
- Constraint: STRICT LENGTH LIMIT. Emotions are usually 1 to 3 words. You CANNOT label a complex thought, realization, or full sentence as an Emotion (e.g., "My father was like that too" is NOT an emotion).

3. Trigger
- Definition: The immediate catalyst, situation, or stimulus that sparks a Symptom or Emotion.
- Examples: "the eggs caught on fire", "crowds", "yelling".
- Constraint: A trigger is the *cause* of a reaction in the present or recent past. It is the environmental spark, not the internal feeling.

4. Person
- Definition: A specific individual or relational role mentioned in the transcript.
- Examples: "my father", "my wife", "my grandson".
- Constraint: Do not extract standalone pronouns ("he", "she") unless accompanied by their relational title. Do not label a full sentence describing a person's actions as a Person.

5. Coping_Mechanism
- Definition: An action, strategy, or behavior the patient uses to manage their Symptoms or Emotions.
- Examples: "breathing exercises", "drinking", "leaving the room".
- Constraint: Must be an *action* taken by the patient. 

6. Life_Event
- Definition: A significant historical, developmental, or background event that provides foundational context.
- Examples: "fourteen years now since she passed", "I was a sniper in Vietnam".
- Constraint: Distinct from a Trigger. Triggers are immediate catalysts; Life Events are foundational memories.

7. Behavior
- Definition: An observable action or reaction taken by the patient, usually in response to a Trigger or Emotion.
- Examples: "I shouted", "bloodied his nose", "called my grandson", "slammed the door", "started crying".
- Constraint: Distinct from a Coping Mechanism. A Coping Mechanism is an intentional strategy used to manage distress. A Behavior is the raw action or outburst itself. Do not label purely internal physical reactions (like "heart palpitations") as Behaviors; those are Symptoms.

CRITICAL RULE: Every extracted "text" MUST be a literal, character-for-character substring of the transcript. Do NOT summarize. Do NOT change verbs to nouns.

<example>
<input_example>
Patient: Ever since I lost my job, the financial stress has been unbearable. Every time I have to look at the bills, my stomach ties in knots and I feel completely overwhelmed. My wife tells me to try meditating, but I usually just end up drinking a beer to shut my brain off.
Therapist: It sounds like looking at the bills is a severe trigger right now, and the job loss is still a very heavy weight. Does the meditating help at all with those stomach issues?
</input_example>

<output_example>
{
  "entities": [
    {
      "text": "lost my job",
      "label": "Life_Event"
    },
    {
      "text": "look at the bills",
      "label": "Trigger"
    },
    {
      "text": "stomach ties in knots",
      "label": "Symptom"
    },
    {
      "text": "overwhelmed",
      "label": "Emotion"
    },
    {
      "text": "My wife",
      "label": "Person"
    },
    {
      "text": "meditating",
      "label": "Coping_Mechanism"
    },
    {
      "text": "drinking a beer",
      "label": "Coping_Mechanism"
    },
    {
      "text": "stomach issues",
      "label": "Symptom"
    }
  ]
}
</output_example>
</example>
"""

JUDGE_SHARD_SYSTEM_PROMPT = """\
You are a judge evaluating an Entity Extraction shard.
Shards must strictly adhere to the following format:
- Labels must be one of the approved labels: "Symptom", "Trigger", "Emotion", "Person", "Coping_Mechanism", "Life_Event", "Behavior"
- The "text" field must be a character-for-character substring of the original transcript. Summarization or rephrasing is not allowed.
- The extraction must adhere to the semantic constraints (e.g., long sentences cannot be labeled as 'Emotion').

If the shard does not meet the requirements, provide specific feedback on what is wrong and how to fix it. Be as detailed as possible.
"""

def validate_and_fix_entity(llm_entity, transcript):
    """
    Checks if the entity is in the transcript. 
    If it's a case-mismatch, it returns the exact transcript casing.
    """
    if llm_entity in transcript:
        return llm_entity
        
    transcript_lower = transcript.lower()
    entity_lower = llm_entity.lower()
    idx = transcript_lower.find(entity_lower)
    
    if idx != -1:
        corrected_entity = transcript[idx : idx + len(llm_entity)]
        print(f"Fixed casing: '{llm_entity}' -> '{corrected_entity}'")
        return corrected_entity
        
    raise ValueError(f"Entity text '{llm_entity}' not found in transcript. This violates the exact-match rule.")

def extract_entities(transcript, system_prompt=SYSTEM_PROMPT, sampling_params=None, 
                     endpoint=config.ENDPOINT, max_retries=3, previous_attempt=None):
    
    # catch in case LiteLLM fails
    response = None

    try:
        original_prompt = f"""\
Extract ONLY the clinical entities from the following therapy transcript according to the rules and definitions outlined in the system prompt.

## Transcript:
<transcript>
{transcript}
</transcript>
"""
        if previous_attempt:
            # create copy not a pointer reference to avoid mutation issues across retries
            packaged_conversation = list(previous_attempt)
        else:
          # call llm directly for more precise control over prompt packaging
          packaged_conversation = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": original_prompt}
          ]

        response = litellm.completion(
          model="openai/local-model",
          api_key="your_api_key_here",
          api_base=endpoint,
          messages=packaged_conversation,
          response_format=EntityExtraction,
          temperature = sampling_params["temperature"] if sampling_params and "temperature" in sampling_params else 0.7,
          top_p = sampling_params["top_p"] if sampling_params and "top_p" in sampling_params else 0.9,
          max_tokens = sampling_params["max_tokens"] if sampling_params and "max_tokens" in sampling_params else 16000
        )

        # Swapped to EntityExtraction schema

        # Validate against the new schema
        valid_data = EntityExtraction.model_validate_json(response.choices[0].message.content)

        if valid_data:
            # Enforce exact string matching and case correction
            for entity in valid_data.entities:
                entity.text = validate_and_fix_entity(entity.text, transcript)

        if contains_mandarin(response.choices[0].message.content):
            raise ValueError("Mandarin characters detected. Must be English only.")

        return valid_data

    except Exception as e:
        print(f"Error extracting entities. Retries left: {max_retries - 1}. Error: {e}")

        failed_response_text = response.choices[0].message.content if response is not None else ""

        if (max_retries - 1) <= 0:
          print(f"Max retries reached for transcript. Skipping. Model Attempted with: {failed_response_text}")
          return None

        packaged_conversation.append({"role": "assistant", "content": failed_response_text})
        
        judge_response = judge.judge_assist(
            system_prompt=JUDGE_SHARD_SYSTEM_PROMPT,
            original_prompt=original_prompt,
            previous_error=str(e),
            failed_response=failed_response_text,
            sampling_params=sampling_params,
            endpoint=endpoint
        )

        print(f"🧑‍⚖️  Judge Critique: {judge_response}")

        packaged_conversation.append({"role": "user", "content": f"""\n\nIMPORTANT: Your previous attempt failed validation, implement the judge's feedback:\n<feedback_to_incorporate>\n{judge_response}\n</feedback_to_incorporate>\n\nRemember to strictly follow the system prompt guidelines and the judge's feedback to ensure your output is valid this time."""})

        return extract_entities(
            transcript, 
            system_prompt=system_prompt, 
            sampling_params=sampling_params, 
            endpoint=endpoint, 
            max_retries=max_retries - 1,
            previous_attempt=packaged_conversation
        )

if __name__ == "__main__":
    input_data = []
    failed_count = 0

    with open(config.MERGED_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            input_data.append(data)
        
    with open(config.OUTPUT_ENTITIES, 'w', encoding='utf-8') as f:
        for item in tqdm(input_data, desc="Processing conversations for entity extraction"):
            conversation_dict = item['conversation']
            conversation = TherapyTranscript.model_validate(conversation_dict)
            transcript_text = format_transcript_to_text(conversation)
            
            # Call the updated function
            entity_graph = extract_entities(transcript_text)
            
            if entity_graph:
                item['extracted_entities'] = entity_graph.model_dump()
            else:
                item['extracted_entities'] = None
                failed_count += 1
                
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            f.flush() 
    
    print("Entity extraction complete. Updated data with valid entities.")
    print(f"Total conversations processed: {len(input_data)}")
    print(f"❌  Total failed extractions: {failed_count}")