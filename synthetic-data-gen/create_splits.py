import os
from datasets import load_dataset, DatasetDict

import config

def create_static_splits(input_file=config.OUTPUT_IOB, output_dir="./datasets/IOB-dataset-splits"):
    print(f"Loading master dataset from {input_file}...")
    raw_dataset = load_dataset("json", data_files=input_file, split="train")

    # 1. First Split: 90% for Train+Val, 10% for Test
    # Using a fixed seed guarantees reproducible splits
    train_test = raw_dataset.train_test_split(test_size=0.1, seed=42)

    # 2. Second Split: Carve 10% of the original total out of the 90% pool for Validation
    train_val = train_test['train'].train_test_split(test_size=0.1111, seed=42)

    # 3. Assemble the DatasetDict
    dataset = DatasetDict({
        'train': train_val['train'],
        'validation': train_val['test'],
        'test': train_test['test']
    })

    # 4. Save to static files
    os.makedirs(output_dir, exist_ok=True)
    
    dataset["train"].to_json(f"{output_dir}/train.jsonl", force_ascii=False)
    dataset["validation"].to_json(f"{output_dir}/val.jsonl", force_ascii=False)
    dataset["test"].to_json(f"{output_dir}/test.jsonl", force_ascii=False)

    print(f"Success! Static splits saved to ./{output_dir}/")
    print(f"Train: {len(dataset['train'])} rows")
    print(f"Val:   {len(dataset['validation'])} rows")
    print(f"Test:  {len(dataset['test'])} rows")

if __name__ == "__main__":
    create_static_splits(config.RE_OUTPUT_FILE, config.RE_SPLIT_DATA_DIR)