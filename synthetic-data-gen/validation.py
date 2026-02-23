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