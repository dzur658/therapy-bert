import torch
from datasets import DatasetDict, load_dataset
from transformers import (
    AutoTokenizer, 
    AutoModelForTokenClassification, 
    TrainingArguments, 
    Trainer, 
    DataCollatorForTokenClassification
)

# 1. Define the exact vocabulary of your Knowledge Graph
UNIQUE_LABELS = [
    "O", 
    "B-Symptom", "I-Symptom", 
    "B-Trigger", "I-Trigger", 
    "B-Emotion", "I-Emotion", 
    "B-Person", "I-Person", 
    "B-Coping_Mechanism", "I-Coping_Mechanism", 
    "B-Life_Event", "I-Life_Event"
]

# Mapping File
MAP_FILE = "./datasets/therapy_conversaitons_iob.json"  # This should be a JSON file that maps your IOB tags to the original entity text and labels for later reference

# Create dictionaries to translate between human strings and computer integers
label2id = {label: i for i, label in enumerate(UNIQUE_LABELS)}
id2label = {i: label for i, label in enumerate(UNIQUE_LABELS)}

# 2. Load the Tokenizer and Model
MODEL_NAME = "answerdotai/ModernBERT-large"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

# We use AutoModelForTokenClassification and pass it our custom label maps
model = AutoModelForTokenClassification.from_pretrained(
    MODEL_NAME,
    num_labels=len(UNIQUE_LABELS),
    id2label=id2label,
    label2id=label2id
)

# 3. Load and Preprocess the Dataset
master_dataset = load_dataset("json", data_files=MAP_FILE, split="train")

# 1. First Split: 90% for Train+Val, 10% for the locked Test set
train_test_split = master_dataset.train_test_split(test_size=0.1)

# 2. Second Split: Out of the 90% Train pool, carve out the Validation set.
# To get exactly 10% of the TOTAL original dataset, we take ~11.1% of the 90% pool (0.1 / 0.9 = 0.1111)
train_val_split = train_test_split['train'].train_test_split(test_size=0.1111)

# 3. Assemble the final 3-part Dictionary
dataset = DatasetDict({
    'train': train_val_split['train'],
    'validation': train_val_split['test'],
    'test': train_test_split['test']
})

def preprocess_function(examples):
    batch_input_ids = []
    batch_attention_mask = []
    batch_labels = []
    
    special_token_ids = set(tokenizer.all_special_ids)
    
    for tokens, tags in zip(examples["tokens"], examples["ner_tags"]):
        # Convert the string tokens (e.g., "Ġpanic") back into integer IDs (e.g., 4598)
        input_ids = tokenizer.convert_tokens_to_ids(tokens)
        
        # Create an attention mask (1 means "pay attention to this token")
        attention_mask = [1] * len(input_ids)
        
        labels = []
        for token_id, tag in zip(input_ids, tags):
            # Pad to -100 so special tokens are ignored in the loss calculation
            if token_id in special_token_ids:
                labels.append(-100)
            else:
                labels.append(label2id[tag])
                
        batch_input_ids.append(input_ids)
        batch_attention_mask.append(attention_mask)
        batch_labels.append(labels)
        
    return {
        "input_ids": batch_input_ids, 
        "attention_mask": batch_attention_mask, 
        "labels": batch_labels
    }

# Apply the preprocessing map and drop the old string columns
tokenized_datasets = dataset.map(
    preprocess_function, 
    batched=True, 
    remove_columns=["tokens", "ner_tags"]
)

# 4. The Data Collator
# This automatically pads your transcripts with 0s so they are all the same length in a batch,
# and it smartly pads your labels with -100 so the model doesn't train on the padding!
data_collator = DataCollatorForTokenClassification(tokenizer=tokenizer)

# 5. Define Training Arguments
training_args = TrainingArguments(
    output_dir="./therapy-modernbert-ner",
    evaluation_strategy="epoch",      # Check performance at the end of each epoch
    learning_rate=2e-5,               # Standard starting rate for fine-tuning BERT
    per_device_train_batch_size=8,    # Adjust down to 4 or 2 if your GPU runs out of memory
    per_device_eval_batch_size=8,
    num_train_epochs=3,               # 3 to 5 epochs is usually the sweet spot for NER
    weight_decay=0.01,
    bf16=True,                        # ModernBERT loves bfloat16 precision for faster training
    logging_steps=50,
    save_strategy="epoch",            # Save a model checkpoint every epoch
)

# 6. Initialize and Launch the Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["validation"],
    tokenizer=tokenizer,
    data_collator=data_collator,
)

if __name__ == "__main__":
    print("Initializing ModernBERT-large training...")
    trainer.train()
    
    # Save the final pristine model to your hard drive
    trainer.save_model("./therapy-modernbert-ner-final")
    print("Training complete! Model saved to ./therapy-modernbert-ner-final")