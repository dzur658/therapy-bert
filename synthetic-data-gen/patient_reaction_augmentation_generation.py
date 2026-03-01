import config
import personas
from validation import TherapyTranscript, contains_mandarin
import judge
import export

import json
import rich

from openai import OpenAI
import litellm
from tqdm import tqdm

# how many augmentation examples to generate
TOTAL_AUG_EXAMPLES = 500
AUGMENATION_OUTPUT_FILE = "./datasets/augmented_conversations.jsonl"

SYSTEM_PROMPT = """\
## Task Description
You are a synthetic data generator for therapy conversations. 
Your task is to create realistic therapy dialogues based on the provided patient and therapist personas. 
Each conversation should reflect the unique characteristics of the patient, including their demographics, 
presenting issues, relationship status, living situation, therapy modality, and speaking styles. 
The therapist's responses should be appropriate to the patient's profile and the context of the conversation as well as session. 
Generate conversations that are coherent, engaging, and representative of real therapy sessions.

## Rules
1. Therapist or patient can start the conversation.
2. A therapist turn should be followed by a patient turn and vice versa.
3. The conversation should reflect the patient's presenting issues and be plausible in the context of the therapy modality.
4. The therapist's responses should be appropriate to the patient's profile and the context of the conversation as well as session.
5. Do not include any preamble or postamble in the conversation. Only include the dialogue turns between the patient and therapist.
6. EPISTEMIC CLASHES: The therapist must occasionally propose clinical hypotheses (e.g., suggesting that a specific trigger causes a symptom). 
7. PATIENT REACTIONS: When the therapist proposes a hypothesis, the patient must react realistically using one of these specific narrative behaviors:
   - "Affirmed": The patient explicitly agrees with the therapist's proposed connection.
   - "Denied": The patient disagrees, refutes, or corrects the therapist's hypothesis.
   - "Avoided": The patient changes the subject, gives a non-committal answer, or gets defensive to avoid the hypothesis.
   - "Realized_Later": The patient admits that a hypothesis they previously denied or ignored in an earlier session is actually true.
8. PATIENT PROPOSALS: The patient should also naturally state their own firm beliefs about what causes or improves their issues.
Rule 9: Include natural conversational boundaries, such as brief small talk, rapport-building, or tangential anecdotes at the beginning or end of the session.

## Example Conversation
<example_input>
Age: 32
Gender: non-binary
Occupation: software engineer
Presenting Issue: imposter syndrome
Relationship Status: single
Living Situation: living alone
Therapy Modality: cognitive-behavioral therapy
Patient Speaking Style: verbose
Therapist Speaking Style: direct
Sessions: 3
Conversation Length: 4
</example_input>

<example_output>
{
    "turns": [
        {"speaker": "Therapist", "text": "We talked last week about tracking your automatic negative thoughts at work. When you completely spiraled after that code review on Tuesday, do you think your panic was triggered by a fear of authority figures?"},
        {"speaker": "Patient", "text": "Actually, no. I really don't care about authority at all, my boss is great. It's the fear of letting my peers down that triggers the panic. I feel like a total fraud to the other developers, so when they left that redundant logic comment, I spent three hours hyperventilating in the bathroom."},
        {"speaker": "Therapist", "text": "That is a crucial distinction. It's not the hierarchy that causes the anxiety, it's the peer evaluation. Last session, I suggested that your imposter syndrome might be making you interpret neutral peer feedback as hostile. How does that sit with you now?"},
        {"speaker": "Patient", "text": "I know I brushed that off last time, but you were right. I realized later that the developer who left the comment actually uses that exact same phrasing with everyone. The comment was neutral, but my brain twisted it into an attack."}
    ]
}
</example_output>
"""

def call_api(prompt, system_prompt=SYSTEM_PROMPT, sampling_params=None, endpoint=config.ENDPOINT, schema=TherapyTranscript):

    packaged_prompt = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    response = litellm.responses(
        model="openai/local-model",
        api_key="your_api_key_here",
        api_base=endpoint,
        input=packaged_prompt,
        text_format=schema,
        temperature = sampling_params["temperature"] if sampling_params and "temperature" in sampling_params else 0.7,
        top_p = sampling_params["top_p"] if sampling_params and "top_p" in sampling_params else 0.9,
        max_tokens = sampling_params["max_tokens"] if sampling_params and "max_tokens" in sampling_params else 16000
    )
    
    # return only the text content of the response
    return response.output_text

def generate_conversation(fingerprint, system_prompt=SYSTEM_PROMPT, sampling_params=None, 
                          endpoint=config.ENDPOINT, max_retries=3, judge_feedback=None):
    # guardrail to protect against infinite recursion
    if max_retries <= 0:
        print(f"Max retries reached for fingerprint {fingerprint}. Skipping this example. Last judge feedback: {judge_feedback}")
        return None

    try:
        # create a prompt based on the fingerprint
        prompt = f"""\
    Generate a therapy conversation based on the following patient and therapist personas:    

    Age: {fingerprint['age']}
    Gender: {fingerprint['gender']}
    Occupation: {fingerprint['occupation']}
    Presenting Issue: {fingerprint['presenting_issue']}
    Relationship Status: {fingerprint['relationship_status']}
    Living Situation: {fingerprint['living_situation']}
    Therapy Modality: {fingerprint['therapy_modality']}
    Patient Speaking Style: {fingerprint['patient_speaking_style']}
    Therapist Speaking Style: {fingerprint['therapist_speaking_style']}
    Session Number: {fingerprint['sessions']}
    Conversation Length: {fingerprint['conversation_length']}
    """
        
        if judge_feedback:
            prompt += f"\n\nIMPORTANT: Your previous attempt failed validation, implement the judge's feedback to fix the response: {judge_feedback}"
        
        conversation = call_api(prompt, system_prompt=system_prompt, sampling_params=sampling_params, endpoint=endpoint)

        # ensure format was followed exactly
        valid_data = TherapyTranscript.model_validate_json(conversation)

        # validate turns are correct
        number_of_turns = len(valid_data.turns)

        if number_of_turns != fingerprint['conversation_length']:
            print(f"Accepting turn count mismatch. Expected {fingerprint['conversation_length']} turns but got {number_of_turns} turns.")
        
        if contains_mandarin(conversation):
            raise ValueError("Mandarin characters detected in conversation, which is not allowed. Conversation must be fully in English.")

        return valid_data

    except Exception as e:
        print(f"Error generating conversation. Retries left: {max_retries - 1}. Error: {e}")

        judge_response = judge.judge_assist(
            original_prompt=prompt,
            previous_error=str(e),
            failed_response=conversation,
            sampling_params=sampling_params,
            endpoint=endpoint
        )

        # print(f"🧑‍⚖️  Judge Critique: {judge_response}")

        # recursive call
        return generate_conversation(
            fingerprint, 
            system_prompt=system_prompt, 
            sampling_params=sampling_params, 
            endpoint=endpoint, 
            max_retries=max_retries - 1, 
            judge_feedback=judge_response
        )

    



if __name__ == "__main__":
    for example in tqdm(range(TOTAL_AUG_EXAMPLES)):
        # generate a random fingerprint for testing
        random_fingerprint = personas.generate_random_fingerprint()
        # print("Generated Fingerprint:")
        # rich.print(random_fingerprint)

        # generate a conversation based on the random fingerprint
        conversation = generate_conversation(random_fingerprint, sampling_params=config.SAMPLING_PARAMS)
        # print("\nGenerated Conversation:")
        # rich.print(conversation)

        # append to jsonl file
        if conversation != None:
            export.write_to_jsonl(conversation, random_fingerprint, AUGMENATION_OUTPUT_FILE)
        else:
            print(f"Failed to generate a valid conversation for fingerprint: {random_fingerprint}. Skipping this example.")