import os
import re
from typing import Dict, List, Optional, Sequence, Tuple, Union

import torch
from huggingface_hub import snapshot_download
from transformers import AutoTokenizer

from modern_bert_re_layers import ModernBERT_Entity_Pooling_RE


MODEL_NAME = "answerdotai/ModernBERT-large"
SPECIAL_TOKENS = {"additional_special_tokens": ["[E1]", "[/E1]", "[E2]", "[/E2]"]}
DEFAULT_MODEL_SOURCE = "./therapy-modernbert-re-final"
DEFAULT_MAX_LENGTH = 8192


def _resolve_model_source(model_source: str) -> str:
	if os.path.isdir(model_source):
		return model_source

	if os.path.isfile(model_source):
		raise ValueError(f"Expected a model directory or HF repo ID, got file path: {model_source}")

	print(f"Resolving Hugging Face snapshot for {model_source}...")
	return snapshot_download(repo_id=model_source)


def load_custom_model(model_source: str = DEFAULT_MODEL_SOURCE):
	resolved_model_dir = _resolve_model_source(model_source)
	print(f"Loading custom RE model from {resolved_model_dir}...")

	try:
		tokenizer = AutoTokenizer.from_pretrained(resolved_model_dir)
	except OSError:
		tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
		tokenizer.add_special_tokens(SPECIAL_TOKENS)

	device = torch.device(
		"cuda"
		if torch.cuda.is_available()
		else "mps"
		if torch.backends.mps.is_available()
		else "cpu"
	)
	model = ModernBERT_Entity_Pooling_RE.from_checkpoint(
		resolved_model_dir,
		tokenizer=tokenizer,
		map_location=device,
	)
	model.eval()
	model.to(device, dtype=torch.bfloat16 if device.type in ["cuda", "mps"] else torch.float32)

	return tokenizer, model, device


def mark_entities(text: str, source: str, target: str) -> str:
	if not source or not target:
		raise ValueError("Both source and target entity strings are required.")

	marked_text = re.sub(f"({re.escape(source)})", r"[E1]\1[/E1]", text, count=1)
	marked_text = re.sub(f"({re.escape(target)})", r"[E2]\1[/E2]", marked_text, count=1)

	if "[E1]" not in marked_text or "[E2]" not in marked_text:
		raise ValueError("Could not find both entities in the provided text.")

	return marked_text


class RelationExtractionInferencePipeline:
	def __init__(self, model_source: str = DEFAULT_MODEL_SOURCE, max_length: int = DEFAULT_MAX_LENGTH):
		self.tokenizer, self.model, self.device = load_custom_model(model_source)
		self.max_length = max_length

	def predict_marked_text(self, marked_text: str, top_k: Optional[int] = 1) -> Union[Dict[str, float], List[Dict[str, float]]]:
		inputs = self.tokenizer(
			marked_text,
			return_tensors="pt",
			truncation=True,
			max_length=self.max_length,
		)
		inputs = {key: value.to(self.device) for key, value in inputs.items()}

		with torch.no_grad():
			outputs = self.model(**inputs)
			logits = outputs["logits"]
			probabilities = torch.softmax(logits, dim=-1)[0]

		scores, indices = torch.sort(probabilities, descending=True)
		predictions = [
			{
				"label": self.model.id2label[int(index)],
				"score": float(score),
			}
			for score, index in zip(scores.tolist(), indices.tolist())
		]

		if top_k is None:
			return predictions

		limited_predictions = predictions[:top_k]

		if top_k == 1:
			return limited_predictions[0]
		else:
			return limited_predictions

		# return limited_predictions[0] if top_k == 1 else limited_predictions

	def predict_relation(
		self,
		text: str,
		source: str,
		target: str,
		top_k: Optional[int] = 1,
	) -> Union[Dict[str, float], List[Dict[str, float]]]:
		marked_text = mark_entities(text, source, target)
		return self.predict_marked_text(marked_text, top_k=top_k)

	def predict_batch(
		self,
		relation_inputs: Sequence[Tuple[str, str, str]],
		top_k: Optional[int] = 1,
	) -> List[Union[Dict[str, float], List[Dict[str, float]]]]:
		marked_inputs = [mark_entities(text, source, target) for text, source, target in relation_inputs]
		encoded = self.tokenizer(
			marked_inputs,
			return_tensors="pt",
			padding=True,
			truncation=True,
			max_length=self.max_length,
		)
		encoded = {key: value.to(self.device) for key, value in encoded.items()}

		with torch.no_grad():
			outputs = self.model(**encoded)
			logits = outputs["logits"]
			probabilities = torch.softmax(logits, dim=-1)

		batch_predictions = []
		for row in probabilities:
			scores, indices = torch.sort(row, descending=True)
			predictions = [
				{
					"label": self.model.id2label[int(index)],
					"score": float(score),
				}
				for score, index in zip(scores.tolist(), indices.tolist())
			]

			if top_k is None:
				batch_predictions.append(predictions)
			elif top_k == 1:
				batch_predictions.append(predictions[0])
			else:
				batch_predictions.append(predictions[:top_k])

		return batch_predictions


if __name__ == "__main__":
	pipeline = RelationExtractionInferencePipeline()

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

	print("\nStarting Relation Extraction Inference...")
	for text, source, target in test_cases:
		result = pipeline.predict_relation(text, source, target, top_k=3)
		print(f"\nText: {text}")
		print(f"Source: {source}")
		print(f"Target: {target}")
		for prediction in result:
			print(f" -> {prediction['label']}: {prediction['score']:.4f}")
