import os

def merge_therapy_conversations(base_conversations_path, aug_conversations_path, output_path):
    # Read conversations from the base dataset
    with open(base_conversations_path, 'r') as f:
        base_conversations = f.read().strip().split('\n')  # Assuming conversations are separated by double newlines

    # Read conversations from the augmented dataset
    with open(aug_conversations_path, 'r') as f:
        aug_conversations = f.read().strip().split('\n')

    # Merge the conversations
    merged_conversations = base_conversations +  aug_conversations

    # Write the merged conversations to the output file
    with open(output_path, 'w') as f:
        f.write('\n'.join(merged_conversations))

if __name__ == "__main__":
    base_conversations_path = "./datasets/therapy_conversations.jsonl"  # Path to the original conversations
    aug_conversations_path = "./datasets/augmented_conversations.jsonl"  # Path to the augmented conversations
    output_path = "./datasets/merged_conversations.jsonl"  # Path to save the merged conversations

    merge_therapy_conversations(base_conversations_path, aug_conversations_path, output_path)
    print(f"Merged conversations saved to {output_path}")