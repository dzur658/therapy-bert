import textwrap

import litellm
from export import format_transcript_to_text
from validation import *
import config
import judge

import json
from typing import List
from tqdm import tqdm
import re

SYSTEM_PROMPT = """\
You are an expert psychiatric data-structuring algorithm. Your task is to map the epistemic relationships between clinical entities in a therapy transcript. 
You will be provided with a transcript and a chronologically ordered Entity Registry. 
IDs are authoritative; source/target IDs must match the ID's text exactly

You will receive:
1) A therapy transcript
2) A locked entity list (already validated)

Your output must be a JSON object matching the RelationExtraction schema with:
<schema>
{
  "relations": [ ... ]
}
</schema>

STRICT RULES:
- Use ONLY entity text strings from the provided entity list as relation source/target.
- Use ONLY entity IDs from the provided entity list as source_id/target_id.
- Do NOT invent new entities.
- Do NOT paraphrase source or target text.
- Do NOT include any boilerplate, explanatory text, or markdown formatting in your response. Output ONLY the JSON object.
- If no valid relations exist, return {"relations": []}.
- Keep directionality clinically accurate.

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

<example>
<input_example>
Patient: Ever since I lost my job, the financial stress has been unbearable. Every time I have to look at the bills, my stomach ties in knots and I feel completely overwhelmed. My wife tells me to try meditating, but I usually just end up drinking a beer to shut my brain off.
Therapist: It sounds like looking at the bills is a severe trigger right now, and the job loss is still a very heavy weight. Does the meditating help at all with those stomach issues?

Provided entities:
[
{"id": "E1", "text": "lost my job", "label": "Life_Event"},
{"id": "E2", "text": "look at the bills", "label": "Trigger"},
{"id": "E3", "text": "stomach ties in knots", "label": "Symptom"},
{"id": "E4", "text": "overwhelmed", "label": "Emotion"},
{"id": "E5", "text": "My wife", "label": "Person"},
{"id": "E6", "text": "meditating", "label": "Coping_Mechanism"},
{"id": "E7", "text": "drinking a beer", "label": "Coping_Mechanism"},
{"id": "E8", "text": "stomach issues", "label": "Symptom"}
]
</input_example>

<output_example>
{
  "relations": [
    {
    "source": "look at the bills",
    "source_id": "E2",
    "predicate": "TRIGGERS",
    "target": "stomach ties in knots",
    "target_id": "E3",
    "proposed_by": "Patient",
    "patient_acceptance": "Affirmed"
    },
    {
    "source": "look at the bills",
    "source_id": "E2",
    "predicate": "TRIGGERS",
    "target": "overwhelmed",
    "target_id": "E4",
    "proposed_by": "Patient",
    "patient_acceptance": "Affirmed"
    },
    {
    "source": "meditating",
    "source_id": "E6",
    "predicate": "IMPROVES",
    "target": "stomach issues",
    "target_id": "E8",
    "proposed_by": "Therapist",
    "patient_acceptance": "Avoided"
    },
    {
    "source": "drinking a beer",
    "source_id": "E7",
    "predicate": "IMPROVES",
    "target": "overwhelmed",
    "target_id": "E4",
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
- Must match KnowledgeGraphExtraction schema with "relations" schema (entities are already provided).
- Relation predicates must be one of: "CAUSES", "WORSENS", "IMPROVES", "RELATES_TO", "EXPERIENCES", "TRIGGERS".
- Relation source/target must be exact members of the provided entity list.
- `proposed_by` must be one of: "Patient", "Therapist".
- `patient_acceptance` must be one of: "Affirmed", "Denied", "Avoided", "Realized_Later".
- If a patient proposes a relation, `patient_acceptance` must be "Affirmed".
- Directionality and semantics of relation must be clinically coherent.

If the shard does not meet the requirements, provide specific feedback on what is wrong and how to fix it. Be as detailed as possible.
"""

def validate_and_fix_relation(relation: Relation) -> Relation:
    if relation.proposed_by == "Patient":
        relation.patient_acceptance = "Affirmed"
    return relation

def safe_json_loads(text: str):
    text = text.strip()

    # protect against markdown fencing
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: grab the first {...} block
        m = re.search(r"\{.*?\}", text, flags=re.DOTALL)
        if not m:
            raise
        return json.loads(m.group(0))

def extract_relations(transcript, entities: List[EntityEnhanced], system_prompt=SYSTEM_PROMPT, sampling_params=None,
                      endpoint=config.ENDPOINT, max_retries=3, previous_attempt=None):
    
    def _safe_get_content(resp) -> str | None:
      """
      Helper function for LiteLLM API failures where the response object may not be well-formed.
      """
      try:
          return resp.choices[0].message.content
      except Exception:
          return None
    
    # catch in case LiteLLM fails
    response = None
    provided_entities = [{"id": entity.id, "text": entity.text, "label": entity.label} for entity in entities]
    id_to_text = {e.id: e.text for e in entities}
    valid_texts = {e.text for e in entities}
    valid_ids = {e.id for e in entities}

    original_prompt = textwrap.dedent(f"""\
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
    """)

    if previous_attempt:
        # create copy not a pointer reference to avoid mutation issues across retries
        packaged_conversation = list(previous_attempt)
    else:
      # call llm directly for more precise control over prompt packaging
      packaged_conversation = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": original_prompt}
      ]

    try:
        response = litellm.completion(
          model="openai/local-model",
          api_key="your_api_key_here",
          api_base=endpoint,
          messages=packaged_conversation,
          response_format=RelationExtraction,
          temperature = sampling_params["temperature"] if sampling_params and "temperature" in sampling_params else 0.7,
          top_p = sampling_params["top_p"] if sampling_params and "top_p" in sampling_params else 0.9,
          max_tokens = sampling_params["max_tokens"] if sampling_params and "max_tokens" in sampling_params else 16000
        )

        content = _safe_get_content(response)
        if not content:
            raise ValueError(f"Empty/invalid model response object: {response!r}")

        if contains_mandarin(content):
            raise ValueError("Mandarin characters detected. Must be English only.")
        
        # take care of accidental markdown wrapping
        relations_payload = safe_json_loads(content)

        # Be tolerant to the model returning either:
        #  - a list of relations
        #  - an object like {"relations": [...]} (or full KG object)
        if isinstance(relations_payload, list):
            relations_payload = {"relations": relations_payload}
        
        # validate relations first, we can fix ids later
        rel_extraction = RelationExtraction.model_validate(relations_payload)

        # Normalize + enforce referential integrity
        for rel in rel_extraction.relations:
            # IDs must exist
            if rel.source_id not in valid_ids:
                raise ValueError(f"Unknown source_id: {rel.source_id}")
            if rel.target_id not in valid_ids:
                raise ValueError(f"Unknown target_id: {rel.target_id}")

            # Force text to canonical registry text based on IDs
            rel.source = id_to_text[rel.source_id]
            rel.target = id_to_text[rel.target_id]

            # Enforce patient acceptance rule
            rel = validate_and_fix_relation(rel)

            # Extra guard: texts must be from list
            if rel.source not in valid_texts or rel.target not in valid_texts:
                raise ValueError("Relation source/target text not in provided entity list.")
        
        # Deduplicate + remove self-relations (after canonicalization)
        seen = set()
        cleaned = []
        for rel in rel_extraction.relations:
            if rel.source_id == rel.target_id:
                continue

            key = (
                rel.source_id,
                rel.predicate,
                rel.target_id,
                getattr(rel, "proposed_by", None),
                getattr(rel, "patient_acceptance", None),
            )
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(rel)

        rel_extraction.relations = cleaned
        
        full_kg_shard = {
            "entities": [e.model_dump() for e in entities],
            "relations": [r.model_dump() for r in rel_extraction.relations]
        }

        valid_data = KnowledgeGraphExtraction.model_validate(full_kg_shard)

        return valid_data

    except Exception as e:
        print(f"Error extracting relations. Retries left: {max_retries - 1}. Error: {e}")

        failed_response_text = None
        if response is not None:
            failed_response_text = _safe_get_content(response) or str(response)

        if not failed_response_text:
            failed_response_text = f"API/System Error: {str(e)}"

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

    with open(config.OUTPUT_ENTITY_MAP, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            input_data.append(data)

    with open(config.OUTPUT_SHARDS, 'w', encoding='utf-8') as f:
        for item in tqdm(input_data, desc="Processing conversations for relation extraction"):
            conversation_dict = item['conversation']
            conversation = TherapyTranscript.model_validate(conversation_dict)
            transcript_text = item["full_transcript"]

            extracted_entities_payload = item.get('entity_map')

            # initialize entities list
            entities_list = None

            # check for missing entities and skip
            if isinstance(extracted_entities_payload, dict):
                entities_list = extracted_entities_payload.get("entities", [])
                
            if (not extracted_entities_payload) or (entities_list is None) or (len(entities_list) == 0):
                item['knowledge_graph_shard'] = None
                skipped_no_entities_count += 1
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
                f.flush()
                continue

            validated_entities = EntityExtractionEnhanced.model_validate(extracted_entities_payload).entities

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