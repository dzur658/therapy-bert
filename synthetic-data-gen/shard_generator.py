from generator import call_api
from export import format_transcript_to_text
from validation import TherapyTranscript, KnowledgeGraphExtraction
import config

import json
from tqdm import tqdm

SYSTEM_PROMPT = """\
You are an expert clinical data extractor. Your job is to read a therapy transcript and extract a Knowledge Graph.
You must extract the exact, messy phrasing used by the patient as the entity "text", but you must strictly categorize them using only the approved Labels and Predicates.

APPROVED LABELS: "Symptom", "Trigger", "Emotion", "Person", "Coping_Mechanism", "Life_Event"
APPROVED PREDICATES: "CAUSES", "WORSENS", "IMPROVES", "RELATES_TO", "EXPERIENCES"

CRITICAL RULE: Every extracted "text" MUST be a literal, character-for-character substring of the transcript. Do NOT summarize. Do NOT change verbs to nouns (e.g., if the patient says "isolated", do not extract "isolation"). 

NOTE: Sources and targets must be defined in the entities list. New sources and targets are not allowed to be defined in the relations without first being defined in the entities. If an entity is mentioned in the relations that is not defined in the entities list, this is a validation error.

<example>

<input_example>
Therapist: How did you handle the presentation on Tuesday?
Patient: I was absolutely terrified of my boss judging me, so I stayed up all night practicing the slides. But the lack of sleep just gave me a massive migraine during the actual meeting, which made me feel even more incompetent.
</input_example>

<output_example>
{
  "entities": [
    {
      "text": "presentation",
      "label": "Life_Event"
    },
    {
      "text": "terrified",
      "label": "Emotion"
    },
    {
      "text": "my boss",
      "label": "Person"
    },
    {
      "text": "stayed up all night practicing",
      "label": "Coping_Mechanism"
    },
    {
      "text": "lack of sleep",
      "label": "Symptom"
    },
    {
      "text": "massive migraine",
      "label": "Symptom"
    },
    {
      "text": "incompetent",
      "label": "Emotion"
    }
  ],
  "relations": [
    {
      "source": "presentation",
      "predicate": "CAUSES",
      "target": "terrified"
    },
    {
      "source": "my boss",
      "predicate": "RELATES_TO",
      "target": "terrified"
    },
    {
      "source": "terrified",
      "predicate": "CAUSES",
      "target": "stayed up all night practicing"
    },
    {
      "source": "stayed up all night practicing",
      "predicate": "CAUSES",
      "target": "lack of sleep"
    },
    {
      "source": "lack of sleep",
      "predicate": "CAUSES",
      "target": "massive migraine"
    },
    {
      "source": "massive migraine",
      "predicate": "WORSENS",
      "target": "incompetent"
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
        
    with open(config.OUTPUT_IOB, 'w', encoding='utf-8') as f:
        for item in tqdm(input_data, desc="Processing conversations for knowledge graph extraction"):
            conversation_dict = item['conversation']
            conversation = TherapyTranscript.model_validate(conversation_dict)
            transcript_text = format_transcript_to_text(conversation)
            knowledge_graph = generate_knowledge_graph(transcript_text)
            item['knowledge_graph_shard'] = knowledge_graph.model_dump() if knowledge_graph else None
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            f.flush()  # Ensure each line is written to disk immediately
    
    print("Knowledge graph extraction complete. Updated data with knowledge graph shards.")
