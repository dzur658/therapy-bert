from pydantic import BaseModel, Field, model_validator
from typing import List, Literal

class DialogueTurn(BaseModel):
    # 'Literal' forces the LLM to strictly choose one of these two strings
    speaker: Literal["Therapist", "Patient"]
    text: str = Field(..., description="The exact words spoken by the person.")

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
    label: Literal["Symptom", "Trigger", "Emotion", "Person", "Coping_Mechanism", "Life_Event"] = Field(
        ..., description="The clinical category of the entity."
    )

# --- 2. The Edges (Relations) ---
class Relation(BaseModel):
    source: str = Field(..., description="The text of the source entity.")
    predicate: Literal["CAUSES", "WORSENS", "IMPROVES", "RELATES_TO", "EXPERIENCES"] = Field(
        ..., description="The strict relationship type."
    )
    target: str = Field(..., description="The text of the target entity.")

# --- 3. The Master Graph Object ---
class KnowledgeGraphExtraction(BaseModel):
    entities: List[Entity] = Field(..., description="List of all clinical entities found.")
    relations: List[Relation] = Field(..., description="List of how those entities connect.")

    @model_validator(mode='after')
    def check_referential_integrity(self) -> 'KnowledgeGraphExtraction':
        # 1. Create a fast-lookup set of all the entity text strings the LLM found
        valid_entity_texts = {entity.text for entity in self.entities}
        
        # 2. Inspect every single relation
        for i, rel in enumerate(self.relations):
            # 3. The Enforcement Logic: Does the source exist in our mugshot pile?
            if rel.source not in valid_entity_texts:
                raise ValueError(
                    f"Referential Error in relation {i}: The source entity '{rel.source}' "
                    f"was used in a relationship, but was never defined in the entities list."
                )
            # 4. Does the target exist in our mugshot pile?
            if rel.target not in valid_entity_texts:
                raise ValueError(
                    f"Referential Error in relation {i}: The target entity '{rel.target}' "
                    f"was used in a relationship, but was never defined in the entities list."
                )
                
        return self