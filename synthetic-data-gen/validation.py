from pydantic import BaseModel, Field, model_validator, field_validator
from typing import List, Literal
import re

class DialogueTurn(BaseModel):
    # MiniMax likes to shorten roles to match clinical transcripts, so we correct these on the fly
    speaker: str = Field(..., description="Either 'Patient' or 'Therapist'")
    text: str = Field(..., description="The dialogue text")

    @field_validator('speaker', mode='before')
    @classmethod
    def clean_speaker_name(cls, value: str) -> str:
        # Intercept Minimax's weird "therap" hallucination
        if value.lower().strip() in ['therap', 'therap.', 'therapist']:
            return 'Therapist'
        if value.lower().strip() in ['pat', 'patient']:
            return 'Patient'
        
        return value

    @field_validator('speaker')
    @classmethod
    def enforce_literal(cls, value: str) -> str:
        # Now we enforce the strict rule AFTER we cleaned the data
        if value not in ['Therapist', 'Patient']:
            raise ValueError(f"Speaker must be Therapist or Patient, got: {value}")
        return value

class TherapyTranscript(BaseModel):
    turns: List[DialogueTurn] = Field(..., description="A list of alternating dialogue turns.")

    @model_validator(mode='after')
    def check_alternating_speakers(self) -> 'TherapyTranscript':
        # If there are no turns, there's nothing to validate
        if not self.turns:
            raise ValueError("Conversation must contain at least one turn.")
            
        # Iterate through the list of turns, starting from the second item
        for i in range(1, len(self.turns)):
            current_speaker = self.turns[i].speaker
            previous_speaker = self.turns[i-1].speaker
            
            # The Enforcement Logic:
            if current_speaker == previous_speaker:
                raise ValueError(
                    f"Conversation schema broken at turn {i+1}. "
                    f"Speaker '{current_speaker}' spoke twice in a row. "
                    f"Must alternate between Therapist and Patient."
                )
                
        return self

# --- 1. The Nodes (Entities) ---
class Entity(BaseModel):
    text: str = Field(..., description="The exact text snippet from the dialogue.")
    label: Literal["Symptom", "Trigger", "Emotion", "Person", "Coping_Mechanism", "Life_Event", "Behavior"] = Field(
        ..., description="The clinical category of the entity."
    )

# for kg shard generation
class EntityEnhanced(Entity):
    text: str = Field(..., description="The exact text snippet from the dialogue.")
    label: Literal["Symptom", "Trigger", "Emotion", "Person", "Coping_Mechanism", "Life_Event", "Behavior"] = Field(
        ..., description="The clinical category of the entity."
    )
    start: int = Field(..., description="The starting character index of this entity in the full transcript.")
    end: int = Field(..., description="The ending character index of this entity in the full transcript.")
    id: str = Field(..., description="A unique ID for this entity (e.g., 'E1', 'E2', etc.)")

# For validating on Entity Pass
class EntityExtraction(BaseModel):
    entities: List[Entity]

# For validating Entities on Relation Pass
class EntityExtractionEnhanced(BaseModel):
    entities: List[EntityEnhanced]

# --- 2. The Edges (Relations) ---
class Relation(BaseModel):
    source: str = Field(..., description="The text of the source entity.")
    source_id: str = Field(..., description="The exact ID of the source entity from the provided registry (e.g., 'E1').")

    predicate: Literal["CAUSES", "WORSENS", "IMPROVES", "RELATES_TO", "EXPERIENCES", "TRIGGERS"] = Field(
        ..., description="The strict relationship type."
    )

    target: str = Field(..., description="The text of the target entity.")
    target_id: str = Field(..., description="The exact ID of the target entity from the provided registry (e.g., 'E2').")

    # EPISTEMIC TRACKERS
    proposed_by: Literal["Patient", "Therapist"] = Field(
        ..., description="Who first introduced this specific relationship?"
    )
    patient_acceptance: Literal["Affirmed", "Denied", "Avoided", "Realized_Later"] = Field(
        ..., description="How did the patient react to this relationship being suggested?"
    )

class RelationExtraction(BaseModel):
    relations: List[Relation]

# --- 3. The Master Graph Object ---
class KnowledgeGraphExtraction(BaseModel):
    entities: List[EntityEnhanced] = Field(..., description="List of all clinical entities found.")
    relations: List[Relation] = Field(..., description="List of how those entities connect.")

    @model_validator(mode='after')
    def check_referential_integrity(self) -> 'KnowledgeGraphExtraction':
        # 1. Create a fast-lookup set of all the entity text strings the LLM found
        valid_entity_texts = {entity.text for entity in self.entities}
        valid_entity_ids = {entity.id for entity in self.entities}
        
        # 2. Inspect every single relation
        for i, rel in enumerate(self.relations):
            # 3. The Enforcement Logic: Does the source exist in the entity pile?
            if rel.source not in valid_entity_texts:
                raise ValueError(
                    f"Referential Error in relation {i}: The source entity '{rel.source}' "
                    f"was used in a relationship, but was never defined in the entities list."
                )
            # 4. Does the target exist in the entity pile?
            if rel.target not in valid_entity_texts:
                raise ValueError(
                    f"Referential Error in relation {i}: The target entity '{rel.target}' "
                    f"was used in a relationship, but was never defined in the entities list."
                )
            # 5. Does the source ID exist in the entity pile?
            if rel.source_id not in valid_entity_ids:
                raise ValueError(
                    f"Referential Error in relation {i}: The source entity ID '{rel.source_id}' "
                    f"was used in a relationship, but was never defined in the entities list."
                )
            # 6. Does the target ID exist in the entity pile?
            if rel.target_id not in valid_entity_ids:
                raise ValueError(
                    f"Referential Error in relation {i}: The target entity ID '{rel.target_id}' "
                    f"was used in a relationship, but was never defined in the entities list."
                )
        return self
    
def contains_mandarin(text: str) -> bool:
    """
    Check for Mandarian characters based off their unicode range.
    """
    # \u4e00-\u9FFF is the core unicode block for Chinese characters
    mandarin_pattern = re.compile(r'[\u4e00-\u9FFF]')
    return bool(mandarin_pattern.search(text))