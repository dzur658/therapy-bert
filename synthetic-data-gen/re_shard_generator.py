import litellm
from export import format_transcript_to_text
from validation import TherapyTranscript, EntityExtraction, Entity, Relation, KnowledgeGraphExtraction, contains_mandarin
import config
import judge

import json
from typing import List
from tqdm import tqdm

SYSTEM_PROMPT = """\
You are an expert clinical knowledge-graph extractor.
Your job is to infer ONLY valid clinical relationships between a pre-defined set of entities.

You will receive:
1) A therapy transcript
2) A locked entity list (already validated)

Your output must be a JSON object matching the KnowledgeGraphExtraction schema with:
- "entities": the same entity list provided
- "relations": relation objects using ONLY the provided entities

RELATION LABEL DEFINITIONS:

1. CAUSES
- Definition: Source is a direct cause of target.
- Example: "urgent email" CAUSES "chest immediately got tight"

2. WORSENS
- Definition: Source exacerbates or intensifies target.
- Example: "drinking" WORSENS "insomnia"

3. IMPROVES
- Definition: Source alleviates or helps reduce target.
- Example: "breathing exercises" IMPROVES "panic attack"

4. RELATES_TO
- Definition: Source and target are clinically associated, but not clearly causal.
- Example: "my father" RELATES_TO "old arguments"

5. EXPERIENCES
- Definition: Usually a Person (or patient self-reference) has/undergoes a state, symptom, or emotion.
- Example: "my wife" EXPERIENCES "anxiety"

6. TRIGGERS
- Definition: Source immediately provokes a response in target.
- Example: "crowds" TRIGGERS "panic attack"

EPISTEMIC TRACKERS:

- proposed_by:
  - "Patient" if the patient first introduces the relationship.
  - "Therapist" if the therapist first introduces/suggests it.

- patient_acceptance:
  - "Affirmed": patient agrees explicitly.
  - "Denied": patient rejects it.
  - "Avoided": patient dodges/does not engage.
  - "Realized_Later": relationship is initially uncertain but later accepted/recognized in the transcript.

NOTE: If the patient introduces the relationship, then patient_acceptance must be "Affirmed" as the patient inherently agrees with themselves. If the therapist introduces the relationship, patient_acceptance can be any of the four options depending on the patient's reaction.

STRICT RULES:
- Use ONLY entity text strings from the provided entity list as relation source/target.
- Do NOT invent new entities.
- Do NOT paraphrase entity text.
- If no valid relations exist, return an empty relations list.
- Keep directionality clinically accurate.

<example>
<input_example>
Patient: Ever since I lost my job, the financial stress has been unbearable. Every time I have to look at the bills, my stomach ties in knots and I feel completely overwhelmed. My wife tells me to try meditating, but I usually just end up drinking a beer to shut my brain off.
Therapist: It sounds like looking at the bills is a severe trigger right now, and the job loss is still a very heavy weight. Does the meditating help at all with those stomach issues?

Provided entities:
[
  {"text": "lost my job", "label": "Life_Event"},
  {"text": "look at the bills", "label": "Trigger"},
  {"text": "stomach ties in knots", "label": "Symptom"},
  {"text": "overwhelmed", "label": "Emotion"},
  {"text": "My wife", "label": "Person"},
  {"text": "meditating", "label": "Coping_Mechanism"},
  {"text": "drinking a beer", "label": "Coping_Mechanism"},
  {"text": "stomach issues", "label": "Symptom"}
]
</input_example>

<output_example>
{
  "relations": [
    {
      "source": "look at the bills",
      "predicate": "TRIGGERS",
      "target": "stomach ties in knots",
      "proposed_by": "Patient",
      "patient_acceptance": "Affirmed"
    },
    {
      "source": "look at the bills",
      "predicate": "TRIGGERS",
      "target": "overwhelmed",
      "proposed_by": "Patient",
      "patient_acceptance": "Affirmed"
    },
    {
      "source": "meditating",
      "predicate": "IMPROVES",
      "target": "stomach issues",
      "proposed_by": "Therapist",
      "patient_acceptance": "Avoided"
    },
    {
      "source": "drinking a beer",
      "predicate": "IMPROVES",
      "target": "overwhelmed",
      "proposed_by": "Patient",
      "patient_acceptance": "Affirmed"
    }
  ]
}
</output_example>
</example>
"""

JUDGE_SHARD_SYSTEM_PROMPT = """\
You are a judge evaluating a Knowledge Graph extraction shard.
Shards must strictly adhere to the following format:
- Must match KnowledgeGraphExtraction schema with both "entities" and "relations".
- Relation predicates must be one of: "CAUSES", "WORSENS", "IMPROVES", "RELATES_TO", "EXPERIENCES", "TRIGGERS".
- Relation source/target must be exact members of the provided entity list.
- `proposed_by` must be one of: "Patient", "Therapist".
- `patient_acceptance` must be one of: "Affirmed", "Denied", "Avoided", "Realized_Later".
- If a patient proposes a relation, `patient_acceptance` must be "Affirmed".
- Directionality and semantics of relation must be clinically coherent.

If the shard does not meet the requirements, provide specific feedback on what is wrong and how to fix it. Be as detailed as possible.
"""

def validate_and_fix_entity(llm_entity: str, entities: List[Entity]) -> str:
    """
    Checks if the entity is in the provided, validated entity list.
    If it's a case mismatch, it returns the canonical casing from the entity object.
    """
    valid_entity_texts = [entity.text for entity in entities]

    if llm_entity in valid_entity_texts:
        return llm_entity

    llm_entity_lower = llm_entity.lower()
    for entity in entities:
        if entity.text.lower() == llm_entity_lower:
            print(f"Fixed casing from entity list: '{llm_entity}' -> '{entity.text}'")
            return entity.text

    raise ValueError(
        f"Entity text '{llm_entity}' not found in provided entity list. "
        "This violates referential integrity."
    )

def validate_and_fix_relation(relation: Relation) -> Relation:
    if relation.proposed_by == "Patient":
        relation.patient_acceptance = "Affirmed"
    return relation

def extract_relations(transcript, entities: List[Entity], system_prompt=SYSTEM_PROMPT, sampling_params=None,
                      endpoint=config.ENDPOINT, max_retries=3, previous_attempt=None):
    
    # catch in case LiteLLM fails
    response = None
    provided_entities = [{"text": entity.text, "label": entity.label} for entity in entities]

    try:
        original_prompt = f"""\
      Extract ONLY the valid clinical relations from the transcript using the provided entities.
      Do not add new entities.

## Transcript:
<transcript>
{transcript}
</transcript>

## Provided Entities (locked list):
<entities>
{json.dumps(provided_entities, ensure_ascii=False, indent=2)}
</entities>
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
          response_format=KnowledgeGraphExtraction,
          temperature = sampling_params["temperature"] if sampling_params and "temperature" in sampling_params else 0.7,
          top_p = sampling_params["top_p"] if sampling_params and "top_p" in sampling_params else 0.9,
          max_tokens = sampling_params["max_tokens"] if sampling_params and "max_tokens" in sampling_params else 16000
        )

        if contains_mandarin(response.choices[0].message.content):
            raise ValueError("Mandarin characters detected. Must be English only.")

        valid_data = KnowledgeGraphExtraction.model_validate_json(response.choices[0].message.content)

        if valid_data:
          for relation in valid_data.relations:
            relation.source = validate_and_fix_entity(relation.source, entities)
            relation.target = validate_and_fix_entity(relation.target, entities)
            relation = validate_and_fix_relation(relation)

          valid_data.entities = entities

          valid_entity_texts = {entity.text for entity in entities}
          for relation in valid_data.relations:
            if relation.source not in valid_entity_texts or relation.target not in valid_entity_texts:
              raise ValueError(
                f"Relation uses undefined entity. source='{relation.source}', target='{relation.target}'"
              )

        return valid_data

    except Exception as e:
        print(f"Error extracting relations. Retries left: {max_retries - 1}. Error: {e}")

        failed_response_text = response.choices[0].message.content if response is not None else f"API/System Error: {str(e)}"

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

        return extract_relations(
            transcript,
            entities,
            system_prompt=system_prompt, 
            sampling_params=sampling_params, 
            endpoint=endpoint, 
            max_retries=max_retries - 1,
            previous_attempt=packaged_conversation
        )

if __name__ == "__main__":
    input_data = []
    skipped_no_entities_count = 0
    failed_relations_count = 0

    with open(config.OUTPUT_ENTITIES, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            input_data.append(data)

    with open(config.OUTPUT_SHARDS, 'w', encoding='utf-8') as f:
        for item in tqdm(input_data, desc="Processing conversations for relation extraction"):
            conversation_dict = item['conversation']
            conversation = TherapyTranscript.model_validate(conversation_dict)
            transcript_text = format_transcript_to_text(conversation)

            extracted_entities_payload = item.get('extracted_entities')

            if not extracted_entities_payload:
                item['knowledge_graph_shard'] = None
                skipped_no_entities_count += 1
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                f.flush()
                continue

            validated_entities = EntityExtraction.model_validate(extracted_entities_payload).entities

            kg_shard = extract_relations(transcript_text, validated_entities)

            if kg_shard:
                item['knowledge_graph_shard'] = kg_shard.model_dump()
            else:
                item['knowledge_graph_shard'] = None
                failed_relations_count += 1

            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            f.flush() 

    print("Knowledge graph extraction complete. Updated data with relation shards.")
    print(f"Total conversations processed: {len(input_data)}")
    print(f"⚠️  Skipped due to missing entities: {skipped_no_entities_count}")
    print(f"❌  Total failed relation extractions: {failed_relations_count}")