import config

import litellm
# judge to help when model fails to follow format or validation rules.

JUDGE_SYSTEM_PROMPT = """\
    You are a judge that evaluates whether a given therapy conversation follows the specified format and rules.
    Conversations must strictly adhere to the following format:
    - follow the requested length of the conversation (number of turns)
    - each turn must be labeled with either "Patient:" or "Therapist:" to indicate the speaker
    - each following turn must alternate speakers (i.e., if one turn is "Patient:", the next must be "Therapist:", and so on)
    - the content of each turn must be relevant to the personas and presenting issue provided in the prompt
    - the conversation must be coherent and reflect a realistic therapy session based on the provided personas and presenting issue
    - no physical descriptions, stage directions, or any text outside of the dialogue turns is allowed
    - The returned object must be a properly formatted JSON string that can be parsed into the TherapyTranscript schema, which consists of a list of dialogue turns, where each turn has a speaker (either "Patient" or "Therapist") and the exact text they spoke.

    Instruct the LLM on how to fix it's previous response to meet the requirements of the rules.
"""

def judge_assist(system_prompt=JUDGE_SYSTEM_PROMPT, 
                 sampling_params=None, 
                 endpoint=config.ENDPOINT,
                 original_prompt=None,
                 previous_error=None,
                 failed_response=None):
    # create a prompt for the judge
    prompt = f"""\
    The following conversation failed validation with the following error message:
    <error>
    {previous_error}
    </error>

    The LLM received the following original prompt to generate the conversation:
    <original_prompt>
    {original_prompt}
    </original_prompt>

    Here is the incorrect conversation that the LLM generated:
    <failed_response>
    {failed_response}
    </failed_response>

    Analyze the conversation, and provide feedback on which rules were broken, and what needs to be fixed.
    """
    
    packaged_prompt = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    response = litellm.responses(
        model="openai/local-model",
        api_key="your_api_key_here",
        api_base=endpoint,
        input=packaged_prompt,
        temperature = sampling_params["temperature"] if sampling_params and "temperature" in sampling_params else 0.7,
        top_p = sampling_params["top_p"] if sampling_params and "top_p" in sampling_params else 0.9,
        max_tokens = sampling_params["max_tokens"] if sampling_params and "max_tokens" in sampling_params else 16000
    )
    
    # return only the text content of the response
    return response.output_text