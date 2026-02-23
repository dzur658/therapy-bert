# configuration variables for synthetic data generation
CONVERSATION_LENGTH_MIN = 2
CONVERSATION_LENGTH_MAX = 5

ENDPOINT = "http://localhost:8080/v1"

TOTAL_EXAMPLES = 2
OUTPUT_FILE = "therapy_conversations.jsonl"

SAMPLING_PARAMS = {
    "temperature": 0.6,
    "top_p": 0.95,
    "max_tokens": 2048
}