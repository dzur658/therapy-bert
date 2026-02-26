# configuration variables for synthetic data generation
CONVERSATION_LENGTH_MIN = 10
CONVERSATION_LENGTH_MAX = 20

ENDPOINT = "http://localhost:8090/v1"

TOTAL_EXAMPLES = 2
OUTPUT_FILE = "./datasets/therapy_conversations.jsonl"
OUTPUT_SHARDS = "./datasets/therapy_conversations_shards.jsonl"
OUTPUT_IOB = "./datasets/therapy_conversations_iob.jsonl"

SAMPLING_PARAMS = {
    "temperature": 1.0,
    "top_p": 0.95,
    "max_tokens": 32000
}