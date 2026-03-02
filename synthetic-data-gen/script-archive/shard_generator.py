from generator import call_api
from export import format_transcript_to_text
from validation import TherapyTranscript, KnowledgeGraphExtraction, contains_mandarin
import config
import judge

import json
from tqdm import tqdm

SYSTEM_PROMPT = """\
You are an expert clinical data extractor. Your job is to read a therapy transcript and extract a Knowledge Graph.
You must extract the exact, messy phrasing used by the patient or therapist as the entity "text", but you must strictly categorize them using only the approved Labels and Predicates.

APPROVED ENTITY LABELS: "Symptom", "Trigger", "Emotion", "Person", "Coping_Mechanism", "Life_Event"
APPROVED RELATIONSHIP PREDICATES: "CAUSES", "WORSENS", "IMPROVES", "RELATES_TO", "EXPERIENCES", "TRIGGERS"

CRITICAL RULE 1: Every extracted "text" MUST be a literal, character-for-character substring of the transcript. Do NOT summarize. Do NOT change verbs to nouns (e.g., if the patient says "isolated", do not extract "isolation"). Failure to use the exact text from the transcript will result in a validation error.

CRITICAL RULE 2 (GRAPH INTEGRITY): Sources and targets must be defined in the entities list first. If an entity is mentioned in the relations that is not defined in the entities list, this is a fatal validation error.

CRITICAL RULE 3 (EPISTEMIC TRACKING): Therapy involves hypothesis testing. You must track WHO proposed a relationship and HOW the patient reacted using these two fields for every relation:
- "proposed_by": Must be either "Patient" or "Therapist". (Who explicitly verbalized the connection first?)
- "patient_acceptance": Must be "Affirmed", "Denied", "Avoided", or "Realized_Later". 
*Important*: If the patient proposes the idea themselves, then this is affirmation, and the "patient_acceptance" should be "Affirmed" since they are accepting their own idea.

CRITICAL RULE 4: Do not include any boiler plate or additional commentary in your response. Only respond with the JSON that adheres EXACTLY to the specified format. Any deviation from the format will result in a validation error.

It is crucial to follow all these rules, as the resulting output will be used to train a BERT clinical entity and relation extraction model. The quality of the training data is paramount, so strict adherence to the format and rules is required.

<example>

<input_example>
Patient: I've been getting these terrible migraines every time I have to visit my parents.
Therapist: It sounds like visiting them is a major trigger. Do you think your mother's criticism causes that physical pain?
Patient: No, actually she's been really supportive lately. I think it's just the travel anxiety that triggers the migraines.
</input_example>

<output_example>
{
  "entities": [
    {
      "text": "migraines",
      "label": "Symptom"
    },
    {
      "text": "visit my parents",
      "label": "Trigger"
    },
    {
      "text": "mother's criticism",
      "label": "Trigger"
    },
    {
      "text": "physical pain",
      "label": "Symptom"
    },
    {
      "text": "travel anxiety",
      "label": "Emotion"
    }
  ],
  "relations": [
    {
      "source": "visit my parents",
      "predicate": "CAUSES",
      "target": "migraines",
      "proposed_by": "Patient",
      "patient_acceptance": "Affirmed" 
    },
    {
      "source": "mother's criticism",
      "predicate": "CAUSES",
      "target": "physical pain",
      "proposed_by": "Therapist",
      "patient_acceptance": "Denied"
    },
    {
      "source": "travel anxiety",
      "predicate": "CAUSES",
      "target": "migraines",
      "proposed_by": "Patient",
      "patient_acceptance": "Affirmed"
    }
  ]
}
</output_example>
</example>
"""

JUDGE_SHARD_SYSTEM_PROMPT = """\
    You are a judge that evaluates whether the extracted knowledge graph shard follows the specified format and rules.
    Shards must strictly adhere to the following format:
    - Labels must be one of the approved labels: "Symptom", "Trigger", "Emotion", "Person", "Coping_Mechanism", "Life_Event"
    - Predicates must be one of the approved predicates: "CAUSES", "WORSENS", "IMPROVES", "RELATES_TO", "EXPERIENCES"
    - The text field must be a character for character substring of the original transcript. Summarization or rephrasing is not allowed.
    - Sources and targets must be defined in the entities list character for character.
    - The proposed by field must indicate who first proposed the relationship, either "Patient" or "Therapist".
    - The patient acceptance field must indicate how the patient reacted to the proposed relationship, either "Affirmed", "Denied", "Avoided", or "Realized_Later".
    - If the patient proposed the relationship themselves, the patient acceptance should be "Affirmed" since they are accepting their own idea.

    The resulting output will be used to train a BERT clinical entity and relation extraction model, so strict adherence to the format and rules is required. 
    If the shard does not meet the requirements, provide specific feedback on what is wrong and how to fix it. Be as detailed as possible in your feedback to guide the LLM in correcting its response.
    Reccomend any other logical changes to ensure the best resulting BERT model from each shard.

    Instruct the LLM on how to fix it's previous response to meet the requirements of the rules.
"""

def validate_and_fix_entity(llm_entity, transcript):
    """
    Checks if the entity is in the transcript. 
    If it's a case-mismatch, it returns the exact transcript casing.
    """
    # 1. The happy path (Exact match)
    if llm_entity in transcript:
        return llm_entity
        
    # 2. The LLM capitalized something wrong (Case-insensitive match)
    transcript_lower = transcript.lower()
    entity_lower = llm_entity.lower()
    
    idx = transcript_lower.find(entity_lower)
    
    if idx != -1:
        # We found it! Now extract the exact casing from the original transcript
        corrected_entity = transcript[idx : idx + len(llm_entity)]
        print(f"Fixed casing: '{llm_entity}' -> '{corrected_entity}'")
        return corrected_entity
        
    # 3. It actually hallucinated (e.g., 'tight chest')
    raise ValueError(f"Entity text '{llm_entity}' not found in transcript. This violates the exact-match rule for entities. This should be the exact text the patient used.")

def generate_knowledge_graph(transcript, system_prompt=SYSTEM_PROMPT, sampling_params=None, 
                          endpoint=config.ENDPOINT, max_retries=3, judge_feedback=None):
    # guardrail to protect against infinite recursion
    if max_retries <= 0:
        print(f"Max retries reached for transcript {transcript}. Skipping this example. Judge Feedback: {judge_feedback}")
        return None
    
    # initialize conversation to guard against local API error
    conversation = ""

    try:
        # create a prompt based on the fingerprint
        prompt = f"""\
    Extract the entities and relationships from the following therapy transcript according to the rules and format outlined in the system prompt.

    ## Transcript:
    <transcript>
    {transcript}
    </transcript>
    """
        
        if judge_feedback:
            prompt += f"\n\nIMPORTANT: Your previous attempt failed validation, implement the judge's feedback to fix the response: {judge_feedback}"
        
        conversation = call_api(prompt, system_prompt=system_prompt, 
                                sampling_params=sampling_params, 
                                endpoint=endpoint, 
                                schema=KnowledgeGraphExtraction)

        # ensure format was followed exactly
        valid_data = KnowledgeGraphExtraction.model_validate_json(conversation)

        if valid_data:
            # THE EXACT-MATCH GUARDRAIL
            # Check if every extracted entity is an exact substring of the transcript
            for entity in valid_data.entities:
                entity.text = validate_and_fix_entity(entity.text, transcript)

        # mandarian check
        if contains_mandarin(conversation):
            raise ValueError("Mandarin characters detected in conversation, which is not allowed. Conversation must be fully in English.")

        return valid_data

    except Exception as e:
        print(f"Error generating knowledge graph entry. Retries left: {max_retries - 1}. Error: {e}")
        print("-" * 50)

        # call judge to get feedback on how to fix the response
        judge_response = judge.judge_assist(
            system_prompt=JUDGE_SHARD_SYSTEM_PROMPT,
            original_prompt=prompt,
            previous_error=str(e),
            failed_response=conversation,
            sampling_params=sampling_params,
            endpoint=endpoint
        )

        print(f"🧑‍⚖️  Judge Critique: {judge_response}")

        # recursive call
        return generate_knowledge_graph(
            transcript, 
            system_prompt=system_prompt, 
            sampling_params=sampling_params, 
            endpoint=endpoint, 
            max_retries=max_retries - 1, 
            judge_feedback=judge_response,
        )

if __name__ == "__main__":
    input_data = []
    failed_count = 0

    with open(config.MERGED_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            input_data.append(data)
        
    with open(config.OUTPUT_SHARDS, 'w', encoding='utf-8') as f:
        for item in tqdm(input_data, desc="Processing conversations for knowledge graph extraction"):
            conversation_dict = item['conversation']
            conversation = TherapyTranscript.model_validate(conversation_dict)
            transcript_text = format_transcript_to_text(conversation)
            knowledge_graph = generate_knowledge_graph(transcript_text)
            if knowledge_graph:
                item['knowledge_graph_shard'] = knowledge_graph.model_dump()
            else:
                item['knowledge_graph_shard'] = None
                failed_count += 1
                print(f"❌  Failed to generate knowledge graph for conversation. Total failed so far: {failed_count}")
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            f.flush()  # Ensure each line is written to disk immediately
            break # testing
    
    print("Knowledge graph extraction complete. Updated data with knowledge graph shards.")
    print(f"Total conversations processed: {len(input_data)}")
    print(f"Total failed conversations: {failed_count}")
