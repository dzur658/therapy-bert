import torch
from transformers import AutoTokenizer

# make sure the classification head is present before importing!
from modern_bert_re_layers import ModernBERT_Entity_Pooling_RE

from typing import Dict, List, Optional, Sequence, Tuple, Union
import re

UNIQUE_LABELS = ["NONE", "CAUSES", "WORSENS", "IMPROVES", "RELATES_TO", "EXPERIENCES", "TRIGGERS"]

# here we load the base tokenizer, but since we added 4 new tokens
# for entity extraction we will have to manually add them below
TOKENIZER_MODEL = "answerdotai/ModernBERT-large"
tokenizer = AutoTokenizer.from_pretrained(TOKENIZER_MODEL)

# add special tokens for entity extraction
SPECIAL_TOKENS = {"additional_special_tokens": ["[E1]", "[/E1]", "[E2]", "[/E2]"]}
tokenizer.add_special_tokens(SPECIAL_TOKENS)

# use on cuda, mps, or cpu
# for example cuda
device = torch.device("cuda")

# set path to weights/config
MODEL_PATH = "./therapy-modernbert-re-final"

model = ModernBERT_Entity_Pooling_RE.from_checkpoint(
		MODEL_PATH,
		tokenizer=tokenizer,
		map_location=device,
	)

# set to eval mode for inference
model.eval()

# cast bf16 to cuda/mps, for cpu use fp32 operations
model.to(device, dtype=torch.bfloat16 if device.type in ["cuda", "mps"] else torch.float32)

# example input
test_cases = [
		(
			"My anxiety has been getting worse since the calls from my ex-husband started again.",
			"ex-husband",
			"anxiety",
		),
		(
			"I avoid crowded stores because the flashing lights can trigger a panic attack.",
			"flashing lights",
			"panic attack",
		),
	]

# helper function to extract entities from the text
def mark_entities(text: str, source: str, target: str) -> str:
	if not source or not target:
		raise ValueError("Both source and target entity strings are required.")

	marked_text = re.sub(f"({re.escape(source)})", r"[E1]\1[/E1]", text, count=1)
	marked_text = re.sub(f"({re.escape(target)})", r"[E2]\1[/E2]", marked_text, count=1)

	if "[E1]" not in marked_text or "[E2]" not in marked_text:
		raise ValueError("Could not find both entities in the provided text.")

	return marked_text

# inference function
def predict_marked_text(marked_text: str, top_k: Optional[int] = 1) -> Union[Dict[str, float], List[Dict[str, float]]]:
    # supports full 8192 token context window
    max_len = 8192

    inputs = tokenizer(
        marked_text,
        return_tensors="pt",
        truncation=True,
        max_length=max_len,
    )
    inputs = {key: value.to(device) for key, value in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs["logits"]
        probabilities = torch.softmax(logits, dim=-1)[0]

        scores, indices = torch.sort(probabilities, descending=True)
        predictions = [
            {
                "label": model.id2label[int(index)],
                "score": float(score),
            }
            for score, index in zip(scores.tolist(), indices.tolist())
        ]
        
        if top_k is None:
            return predictions

        limited_predictions = predictions[:top_k ]

        if top_k == 1:
            return limited_predictions
        else:
            return limited_predictions

for case in test_cases:
    print(case)
    text, source, target = case
    marked_text = mark_entities(text, source, target)

    # top k can be passed here otherwise defaults to 1
    predictions = predict_marked_text(marked_text, top_k=3)
    for pred in predictions:
      print(f" -> {pred['label']}: {pred['score']:.4f}")
    print("-" * 80)