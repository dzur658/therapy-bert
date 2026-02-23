from validation import TherapyTranscript
import json

def format_transcript_to_text(validated_transcript: TherapyTranscript) -> str:
    """Converts the validated JSON object back into a readable script."""
    script_lines = [f"{turn.speaker.lower()}: {turn.text}" for turn in validated_transcript.turns]
    return "\n\n".join(script_lines)

def write_to_jsonl(conversation: TherapyTranscript, fingerprint: dict, output_file: str):
    """Writes the conversation to a .jsonl file."""

    unified_json_object = {
        "conversation": conversation.model_dump(),  # Convert the Pydantic model back to a dictionary
        "fingerprint": fingerprint
    }

    with open(output_file, 'a') as f:
        f.write(json.dumps(unified_json_object) + "\n")