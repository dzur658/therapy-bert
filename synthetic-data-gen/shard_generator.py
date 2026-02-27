from generator import call_api
from export import format_transcript_to_text
from validation import TherapyTranscript, KnowledgeGraphExtraction
import config

import json
from tqdm import tqdm

SYSTEM_PROMPT = """\
You are an expert clinical data extractor. Your job is to read a therapy transcript and extract a Knowledge Graph.
You must extract the exact, messy phrasing used by the patient or therapist as the entity "text", but you must strictly categorize them using only the approved Labels and Predicates.

APPROVED LABELS: "Symptom", "Trigger", "Emotion", "Person", "Coping_Mechanism", "Life_Event"
APPROVED PREDICATES: "CAUSES", "WORSENS", "IMPROVES", "RELATES_TO", "EXPERIENCES"

CRITICAL RULE 1: Every extracted "text" MUST be a literal, character-for-character substring of the transcript. Do NOT summarize. Do NOT change verbs to nouns (e.g., if the patient says "isolated", do not extract "isolation"). Failure to use the exact text from the transcript will result in a validation error.

CRITICAL RULE 2 (GRAPH INTEGRITY): Sources and targets must be defined in the entities list first. If an entity is mentioned in the relations that is not defined in the entities list, this is a fatal validation error.

CRITICAL RULE 3 (EPISTEMIC TRACKING): Therapy involves hypothesis testing. You must track WHO proposed a relationship and HOW the patient reacted using these two fields for every relation:
- "proposed_by": Must be either "Patient" or "Therapist". (Who explicitly verbalized the connection first?)
- "patient_acceptance": Must be "Affirmed", "Denied", "Avoided", or "Realized_Later". 
*Important*: If the patient proposes the idea themselves, then this is affirmation, and the "patient_acceptance" should be "Affirmed" since they are accepting their own idea.

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

def generate_knowledge_graph(transcript, system_prompt=SYSTEM_PROMPT, sampling_params=None, 
                          endpoint=config.ENDPOINT, max_retries=3, previous_error=None,
                          previous_attempt=None):
    # guardrail to protect against infinite recursion
    if max_retries <= 0:
        print(f"Max retries reached for transcript {transcript}. Skipping this example. Last error: {previous_error}")
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
        
        if previous_error:
            prompt += f"\n\nIMPORTANT FAIL NUMBER {3 - max_retries}: Your previous attempt failed validation with the following error:\n{previous_error}\n\nPlease ensure that you strictly follow the rules and format outlined in the system prompt to avoid this error. Check you are using proper labels. Previous attempt: <failed_output>{previous_attempt}</failed_output>"
        
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
                if entity.text.strip().lower() not in transcript.lower():
                    print(f"Model Hallucinated: '{entity.text}' is not in the transcript.")
                    raise ValueError(f"Entity text '{entity.text}' not found in transcript. This violates the exact-match rule for entities. This should be the exact text the patient used.")

        return valid_data

    except Exception as e:
        print(f"Error generating knowledge graph entry. Retries left: {max_retries - 1}. Error: {e}")
        print("-" * 50)

        # recursive call
        return generate_knowledge_graph(
            transcript, 
            system_prompt=system_prompt, 
            sampling_params=sampling_params, 
            endpoint=endpoint, 
            max_retries=max_retries - 1, 
            previous_error=str(e),
            previous_attempt=conversation
        )

if __name__ == "__main__":
    input_data = []

    with open(config.OUTPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            input_data.append(data)
        
    with open(config.OUTPUT_SHARDS, 'w', encoding='utf-8') as f:
        for item in tqdm(input_data, desc="Processing conversations for knowledge graph extraction"):
            conversation_dict = item['conversation']
            conversation = TherapyTranscript.model_validate(conversation_dict)
            transcript_text = format_transcript_to_text(conversation)
            knowledge_graph = generate_knowledge_graph(transcript_text)
            item['knowledge_graph_shard'] = knowledge_graph.model_dump() if knowledge_graph else None
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            f.flush()  # Ensure each line is written to disk immediately
    
    print("Knowledge graph extraction complete. Updated data with knowledge graph shards.")
