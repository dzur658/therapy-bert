import config
import personas
from validation import TherapyTranscript
import export
import judge

import json
import rich

from openai import OpenAI
import litellm
from tqdm import tqdm

SYSTEM_PROMPT = """\

## Task Description
You are a synthetic data generator for therapy conversations. \
Your task is to create realistic therapy dialogues based on the provided patient and therapist personas. \
Each conversation should reflect the unique characteristics of the patient, including their demographics, \
presenting issues, relationship status, living situation, therapy modality, and speaking styles. \
The therapist's responses should be appropriate to the patient's profile and the context of the conversation as well as session. \
Generate conversations that are coherent, engaging, and representative of real therapy sessions.

## Rules
1. Therapist or patient can start the conversation
2. A therapist turn should be followed by a patient turn and vice versa
3. The conversation should reflect the patient's presenting issues and be plausible in the context of the therapy modality
4. The therapist's responses should be appropriate to the patient's profile and the context of the conversation as well as session
5. Do not include any preamble or postamble in the conversation. Only include the dialogue turns between the patient and therapist.

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
        {"speaker": "Therapist", "text": "We talked last week about tracking your automatic negative thoughts at work. How did that go?"},
        {"speaker": "Patient", "text": "It was honestly a complete disaster. I tried, I really did, but on Tuesday my tech lead left a review on my code saying the logic was redundant. I completely spiraled. I spent three hours hyperventilating in the bathroom because I'm convinced they are going to fire me. I just feel like a total fraud who tricked this company into hiring me."},
        {"speaker": "Therapist", "text": "Let's look at the actual evidence. Has your tech lead or manager ever threatened to fire you?"},
        {"speaker": "Patient", "text": "Well, no. My last performance review was actually exceeding expectations. But the anxiety just overrides all of that logic. The code review just felt like undeniable proof that I don't belong here."}
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
        print(f"Max retries reached for fingerprint {fingerprint}. Skipping this example. Judge Feedback: {judge_feedback}")
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
            raise ValueError(f"Conversation length mismatch. Expected {fingerprint['conversation_length']} turns but got {number_of_turns} turns.")

        return valid_data

    except Exception as e:
        print(f"Error generating conversation. Retries left: {max_retries - 1}. Error: {e}")

        # call judge to get feedback on how to fix the response
        judge_response = judge.judge_assist(
            original_prompt=prompt,
            previous_error=str(e),
            failed_response=conversation,
            sampling_params=sampling_params,
            endpoint=endpoint
        )

        print(f"🧑‍⚖️  Judge Critique: {judge_response}")

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
    for example in tqdm(range(config.TOTAL_EXAMPLES)):
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
            export.write_to_jsonl(conversation, random_fingerprint, config.OUTPUT_FILE)
        else:
            print(f"Failed to generate a valid conversation for fingerprint: {random_fingerprint}. Skipping this example.")