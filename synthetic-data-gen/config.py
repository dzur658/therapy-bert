# configuration variables for synthetic data generation
CONVERSATION_LENGTH_MIN = 10
CONVERSATION_LENGTH_MAX = 20

ENDPOINT = "http://localhost:8090/v1"

TOTAL_EXAMPLES = 3000

# these data files are in the order they are generated in the pipeline
OUTPUT_FILE = "./datasets/therapy_conversations.jsonl"
MERGED_FILE = "./datasets/merged_conversations.jsonl"
OUTPUT_ENTITIES = "./datasets/therapy_conversations_entities.jsonl"
OUTPUT_ENTITY_MAP = "./datasets/therapy_conversations_entity_map.jsonl"
OUTPUT_SHARDS = "./datasets/therapy_conversations_shards.jsonl"
CLEAN_DATA = "./datasets/therapy_conversations_clean.jsonl"
OUTPUT_IOB = "./datasets/therapy_conversations_iob.jsonl"
MAP_DIR = "synthetic-data-gen/datasets/IOB-dataset-splits"
RE_OUTPUT_FILE = "./datasets/re_master_data.jsonl"
RE_TRAINING_DATA_DIR = "./datasets/re_datasets"

SAMPLING_PARAMS = {
    "temperature": 1.0,
    "top_p": 0.95,
    "max_tokens": 32000
}
