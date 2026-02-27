# configuration variables for synthetic data generation
CONVERSATION_LENGTH_MIN = 10
CONVERSATION_LENGTH_MAX = 20

ENDPOINT = "http://localhost:8090/v1"

TOTAL_EXAMPLES = 3000
OUTPUT_FILE = "./datasets/therapy_conversations.jsonl"
OUTPUT_SHARDS = "./datasets/therapy_conversations_shards.jsonl"
OUTPUT_IOB = "./datasets/therapy_conversations_iob.jsonl"
MAP_DIR = "synthetic-data-gen/datasets/IOB-dataset-splits"
RE_OUTPUT_FILE = "./datasets/re_master_data.jsonl"

SAMPLING_PARAMS = {
    "temperature": 1.0,
    "top_p": 0.95,
    "max_tokens": 32000
}
