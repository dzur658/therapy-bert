from __future__ import annotations

import bisect
import importlib.util
import itertools
import re
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, get_args

import spacy
import torch
import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ladybug_db.db_manager import PatientGraphDB
from ner_inference_pipeline import extract_entities, load_custom_model
from re_inference_pipeline import RelationExtractionInferencePipeline, mark_entities

import gc


DEFAULT_MAX_CONTEXT_TOKENS = 4096
DEFAULT_WINDOW_OVERLAP_TOKENS = 1000
DEFAULT_RELATION_BATCH_SIZE = 8
PLACEHOLDER_PROPOSED_BY = "PENDING_FUTURE_MODEL"
PLACEHOLDER_PATIENT_ACCEPTANCE = "PENDING_FUTURE_MODEL"


def load_validation_module():
	module_path = "validation.py"
	spec = importlib.util.spec_from_file_location("therapy_validation", module_path)
	if spec is None or spec.loader is None:
		raise ImportError(f"Could not load validation module from {module_path}")

	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


validation_module = load_validation_module()
ALLOWED_ENTITY_LABELS = set(get_args(validation_module.Entity.model_fields["label"].annotation))
ALLOWED_RELATION_PREDICATES = set(get_args(validation_module.Relation.model_fields["predicate"].annotation))


app = FastAPI(title="Therapy Knowledge Graph API")

app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=False,
	allow_methods=["*"],
	allow_headers=["*"],
)

job_store: Dict[str, dict] = {}


class TranscriptTurn(BaseModel):
	speaker: str
	text: str


class DiarizationTranscriptPayload(BaseModel):
	transcript: List[TranscriptTurn]


class InferenceConfig(BaseModel):
	max_context_tokens: int = Field(default=DEFAULT_MAX_CONTEXT_TOKENS, gt=1)
	window_overlap_tokens: int = Field(default=DEFAULT_WINDOW_OVERLAP_TOKENS, ge=0)
	relation_batch_size: int = Field(default=DEFAULT_RELATION_BATCH_SIZE, gt=0)


class KnowledgeGraphRequest(BaseModel):
	patient_id: str | int
	transcript_payload: DiarizationTranscriptPayload
	inference_config: InferenceConfig = Field(default_factory=InferenceConfig)


@dataclass(frozen=True)
class ReconstructedTurn:
	speaker: str
	text: str
	formatted_text: str
	start_char: int
	end_char: int


@dataclass(frozen=True)
class ChunkUnit:
	text: str
	start_char: int
	end_char: int
	start_token: int
	end_token: int


@dataclass(frozen=True)
class TranscriptWindow:
	index: int
	text: str
	start_char: int
	end_char: int
	start_token: int
	end_token: int

	@property
	def center_token(self) -> float:
		return (self.start_token + self.end_token) / 2.0


def normalize_entity_text(text: str) -> str:
	return re.sub(r"\s+", " ", text).strip()


def reconstruct_transcript(payload: DiarizationTranscriptPayload) -> tuple[str, List[ReconstructedTurn]]:
	transcript_parts: List[str] = []
	turns: List[ReconstructedTurn] = []
	cursor = 0

	for item in payload.transcript:
		text = item.text.strip()
		if not text:
			continue

		speaker = item.speaker.strip()
		formatted_text = f"{speaker}: {text}"

		if transcript_parts:
			transcript_parts.append("\n\n")
			cursor += 2

		start_char = cursor
		transcript_parts.append(formatted_text)
		cursor += len(formatted_text)
		end_char = cursor

		turns.append(
			ReconstructedTurn(
				speaker=speaker,
				text=text,
				formatted_text=formatted_text,
				start_char=start_char,
				end_char=end_char,
			)
		)

	transcript_text = "".join(transcript_parts)
	print("Reconstructed Transcript Text As:")
	print(transcript_text[:500] + "..." if len(transcript_text) > 500 else transcript_text)
	return transcript_text, turns


@lru_cache(maxsize=1)
def get_spacy_nlp():
	nlp = spacy.blank("en")
	if "sentencizer" not in nlp.pipe_names:
		nlp.add_pipe("sentencizer")
	return nlp


def split_span_by_sentences_or_tokens(doc, start_char: int, end_char: int, max_tokens: int) -> List[ChunkUnit]:
	nlp = get_spacy_nlp()
	local_text = doc.text[start_char:end_char]
	local_doc = nlp(local_text)
	sentence_spans = [span for span in local_doc.sents if span.text.strip()]
	units: List[ChunkUnit] = []

	if not sentence_spans:
		sentence_spans = [local_doc[:]]

	for sentence in sentence_spans:
		sentence_length = sentence.end - sentence.start
		if sentence_length <= max_tokens:
			abs_start = start_char + sentence.start_char
			abs_end = start_char + sentence.end_char
			absolute_span = doc.char_span(abs_start, abs_end, alignment_mode="expand")
			if absolute_span is None:
				continue
			units.append(
				ChunkUnit(
					text=doc.text[abs_start:abs_end],
					start_char=abs_start,
					end_char=abs_end,
					start_token=absolute_span.start,
					end_token=absolute_span.end,
				)
			)
			continue

		for token_start in range(sentence.start, sentence.end, max_tokens):
			token_end = min(sentence.end, token_start + max_tokens)
			token_slice = local_doc[token_start:token_end]
			abs_start = start_char + token_slice.start_char
			abs_end = start_char + token_slice.end_char
			absolute_span = doc.char_span(abs_start, abs_end, alignment_mode="expand")
			if absolute_span is None:
				continue
			units.append(
				ChunkUnit(
					text=doc.text[abs_start:abs_end],
					start_char=abs_start,
					end_char=abs_end,
					start_token=absolute_span.start,
					end_token=absolute_span.end,
				)
			)

	return units


def build_chunk_units(doc, turns: List[ReconstructedTurn], max_tokens: int) -> List[ChunkUnit]:
	units: List[ChunkUnit] = []

	for turn in turns:
		turn_span = doc.char_span(turn.start_char, turn.end_char, alignment_mode="expand")
		if turn_span is None:
			continue

		token_count = turn_span.end - turn_span.start
		if token_count <= max_tokens:
			units.append(
				ChunkUnit(
					text=turn.formatted_text,
					start_char=turn.start_char,
					end_char=turn.end_char,
					start_token=turn_span.start,
					end_token=turn_span.end,
				)
			)
			continue

		units.extend(split_span_by_sentences_or_tokens(doc, turn.start_char, turn.end_char, max_tokens))

	return units


def build_windows(doc, turns: List[ReconstructedTurn], max_tokens: int, overlap_tokens: int) -> List[TranscriptWindow]:
	if len(doc) == 0:
		return []

	if len(doc) <= max_tokens:
		return [
			TranscriptWindow(
				index=0,
				text=doc.text,
				start_char=0,
				end_char=len(doc.text),
				start_token=0,
				end_token=len(doc),
			)
		]

	safe_overlap = min(overlap_tokens, max_tokens - 1)
	units = build_chunk_units(doc, turns, max_tokens)
	if not units:
		return [
			TranscriptWindow(
				index=0,
				text=doc.text,
				start_char=0,
				end_char=len(doc.text),
				start_token=0,
				end_token=min(len(doc), max_tokens),
			)
		]

	windows: List[TranscriptWindow] = []
	unit_end_tokens = [unit.end_token for unit in units]
	start_idx = 0

	while start_idx < len(units):
		start_unit = units[start_idx]
		end_idx = start_idx

		while end_idx < len(units) and units[end_idx].end_token - start_unit.start_token <= max_tokens:
			end_idx += 1

		if end_idx == start_idx:
			end_idx += 1

		end_unit = units[end_idx - 1]
		windows.append(
			TranscriptWindow(
				index=len(windows),
				text=doc.text[start_unit.start_char:end_unit.end_char],
				start_char=start_unit.start_char,
				end_char=end_unit.end_char,
				start_token=start_unit.start_token,
				end_token=end_unit.end_token,
			)
		)

		if end_idx >= len(units):
			break

		next_start_target = max(start_unit.start_token + 1, end_unit.end_token - safe_overlap)
		next_start_idx = bisect.bisect_right(unit_end_tokens, next_start_target)
		if next_start_idx <= start_idx:
			next_start_idx = start_idx + 1
		start_idx = next_start_idx

	return windows


def locate_anchor_token(doc, window: TranscriptWindow, entity_text: str) -> float:
	pattern = re.compile(re.escape(entity_text), flags=re.IGNORECASE)
	best_anchor = window.center_token
	best_distance = float("inf")

	for match in pattern.finditer(window.text):
		abs_start = window.start_char + match.start()
		abs_end = window.start_char + match.end()
		span = doc.char_span(abs_start, abs_end, alignment_mode="expand")
		if span is None:
			continue

		anchor = (span.start + span.end) / 2.0
		distance = abs(anchor - window.center_token)
		if distance < best_distance:
			best_distance = distance
			best_anchor = anchor

	return best_anchor


def center_weight(window: TranscriptWindow, anchor_token: float) -> float:
	half_width = max((window.end_token - window.start_token) / 2.0, 1.0)
	distance = abs(anchor_token - window.center_token)
	return max(0.0, 1.0 - (distance / half_width))


def parse_relation_predicate(label: str) -> str:
	if label in ALLOWED_RELATION_PREDICATES:
		return label

	for predicate in sorted(ALLOWED_RELATION_PREDICATES, key=len, reverse=True):
		if label.startswith(f"{predicate}_"):
			return predicate

	return label


def extract_chunk_entities(doc, window: TranscriptWindow, tokenizer, model, device) -> Dict[str, dict]:
	ner_output = extract_entities(window.text, tokenizer, model, device)
	raw_entities = ner_output.get("entities", [])
	chunk_entities: Dict[str, dict] = {}

	for entity in raw_entities:
		label = entity.get("type", "").strip()
		text = normalize_entity_text(entity.get("text", ""))
		if not text or not label or label not in ALLOWED_ENTITY_LABELS:
			continue

		anchor_token = locate_anchor_token(doc, window, text)
		weight = center_weight(window, anchor_token)
		key = text.lower()
		candidate = {
			"text": text,
			"label": label,
			"anchor_token": anchor_token,
			"center_weight": weight,
		}

		existing = chunk_entities.get(key)
		if existing is None or candidate["center_weight"] > existing["center_weight"]:
			chunk_entities[key] = candidate

	print(chunk_entities)
	return chunk_entities


def update_master_entities(master_entities: Dict[str, dict], chunk_entities: Dict[str, dict]):
	for key, candidate in chunk_entities.items():
		existing = master_entities.get(key)
		if existing is None or candidate["center_weight"] > existing["center_weight"]:
			master_entities[key] = candidate


def extract_window_relations(window: TranscriptWindow, chunk_entities: Dict[str, dict], relation_batch_size: int, re_pipeline: RelationExtractionInferencePipeline) -> Dict[tuple[str, str, str], dict]:
	entity_texts = [entity["text"] for entity in chunk_entities.values()]
	pair_candidates = list(itertools.permutations(entity_texts, 2))
	valid_inputs: List[tuple[str, str, str]] = []

	for source, target in pair_candidates:
		try:
			mark_entities(window.text, source, target)
		except ValueError:
			continue
		valid_inputs.append((window.text, source, target))

	relation_candidates: Dict[tuple[str, str, str], dict] = {}
	for batch_start in range(0, len(valid_inputs), relation_batch_size):
		batch = valid_inputs[batch_start:batch_start + relation_batch_size]
		predictions = re_pipeline.predict_batch(batch, top_k=1)

		for (chunk_text, source, target), prediction in zip(batch, predictions):
			del chunk_text
			label = prediction.get("label", "NONE")
			if label == "NONE":
				continue
			
			model_score = float(prediction.get("score", 0.0))
			
			if model_score < 0.50:
				continue

			predicate = parse_relation_predicate(label)
			if predicate not in ALLOWED_RELATION_PREDICATES:
				continue

			source_entity = chunk_entities[source.lower()]
			target_entity = chunk_entities[target.lower()]
			anchor_token = (source_entity["anchor_token"] + target_entity["anchor_token"]) / 2.0
			proximity_weight = center_weight(window, anchor_token)
			model_score = float(prediction.get("score", 0.0))
			relation_key = (source.lower(), predicate, target.lower())
			candidate = {
				"source": source_entity["text"],
				"predicate": predicate,
				"target": target_entity["text"],
				"proximity_weight": proximity_weight,
				"model_score": model_score,
			}

			existing = relation_candidates.get(relation_key)
			if existing is None or (candidate["proximity_weight"], candidate["model_score"]) > (
				existing["proximity_weight"],
				existing["model_score"],
			):
				relation_candidates[relation_key] = candidate

	print(relation_candidates)
	return relation_candidates


def build_graph_payload(transcript_text: str, turns: List[ReconstructedTurn], config: InferenceConfig) -> tuple[dict, dict]:
	nlp = get_spacy_nlp()
	doc = nlp(transcript_text)
	windows = build_windows(doc, turns, config.max_context_tokens, config.window_overlap_tokens)

	master_entities: Dict[str, dict] = {}
	master_relations: Dict[tuple[str, str, str], dict] = {}
	window_entities_map: Dict[int, dict] = {}

	print("Loading NER model...")
	ner_tokenizer, ner_model, ner_device = load_custom_model("./therapy-modernbert-ner-final")
	ner_device_type = ner_device.type if hasattr(ner_device, "type") else str(ner_device)

	for window in windows:
		chunk_entities = extract_chunk_entities(doc, window, ner_tokenizer, ner_model, ner_device)
		window_entities_map[window.index] = chunk_entities
		if chunk_entities:
			update_master_entities(master_entities, chunk_entities)

	print("Unloading NER model...")
	del ner_tokenizer
	del ner_model
	gc.collect()
	if ner_device_type == "cuda":
		torch.cuda.empty_cache()
	elif ner_device_type == "mps":
		torch.mps.empty_cache()

	if master_entities:
		print("Loading RE model...")
		re_pipeline = RelationExtractionInferencePipeline(max_length=config.max_context_tokens)

		for window in windows:
			chunk_entities = window_entities_map.get(window.index, {})
			if not chunk_entities:
				continue

			chunk_relations = extract_window_relations(window, chunk_entities, config.relation_batch_size, re_pipeline)

			for key, candidate in chunk_relations.items():
				existing = master_relations.get(key)
				if existing is None or (candidate["proximity_weight"], candidate["model_score"]) > (
					existing["proximity_weight"],
					existing["model_score"],
				):
					master_relations[key] = candidate

		print("Unloading RE model...")
		re_device_type = re_pipeline.device.type if hasattr(re_pipeline.device, "type") else str(re_pipeline.device)
		del re_pipeline
		gc.collect()
		if re_device_type == "cuda":
			torch.cuda.empty_cache()
		elif re_device_type == "mps":
			torch.mps.empty_cache()

	entity_lookup = {entity["text"].lower(): entity for entity in master_entities.values()}
	relations = []
	for relation in sorted(master_relations.values(), key=lambda item: (item["source"].lower(), item["predicate"], item["target"].lower())):
		if relation["source"].lower() not in entity_lookup or relation["target"].lower() not in entity_lookup:
			continue

		# Future pass model will populate the epistemic metadata below.
		proposed_by = PLACEHOLDER_PROPOSED_BY
		patient_acceptance = PLACEHOLDER_PATIENT_ACCEPTANCE
		relations.append(
			{
				"source": relation["source"],
				"predicate": relation["predicate"],
				"target": relation["target"],
				"proposed_by": proposed_by,
				"patient_acceptance": patient_acceptance,
			}
		)

	entities = [
		{"text": entity["text"], "label": entity["label"]}
		for entity in sorted(master_entities.values(), key=lambda item: item["text"].lower())
	]

	payload = {
		"entities": entities,
		"relations": relations,
	}
	stats = {
		"transcript_tokens": len(doc),
		"window_count": len(windows),
		"entity_count": len(entities),
		"relation_count": len(relations),
	}
	return payload, stats


def process_knowledge_graph_job(job_id: str, request_payload: dict):
	try:
		request = KnowledgeGraphRequest.model_validate(request_payload)
		transcript_text, turns = reconstruct_transcript(request.transcript_payload)
		if not transcript_text:
			raise ValueError("Transcript payload did not contain any usable text.")

		graph_payload, stats = build_graph_payload(transcript_text, turns, request.inference_config)
		db = PatientGraphDB(str(request.patient_id))
		db.ingest_bert_payload(graph_payload)

		job_store[job_id]["status"] = "completed"
		job_store[job_id]["result"] = {
			"patient_id": str(request.patient_id),
			"reconstructed_transcript": transcript_text,
			"knowledge_graph": graph_payload,
			"stats": stats,
			"db_summary": {
				"database_path": db.db_path,
				"entities_ingested": len(graph_payload["entities"]),
				"relations_ingested": len(graph_payload["relations"]),
			},
		}
	except Exception as exc:
		job_store[job_id]["status"] = "failed"
		job_store[job_id]["error"] = str(exc)


def export_graph_from_db(patient_id: str) -> dict:
	"""Exports entities and relations from the patient's LadybugDB. Returns empty graph if db doesn't exist."""
	try:
		db = PatientGraphDB(str(patient_id))
		query = """
			MATCH (n)
			OPTIONAL MATCH (n)-[r]->(m)
			RETURN n, r, m
		"""
		results = db.conn.execute(query)
		entities_map: Dict[str, dict] = {}
		relations: List[dict] = []
		seen_relation_keys: set = set()

		while results.has_next():
			row = results.get_next()
			node_1 = row[0]
			relation = row[1]
			node_2 = row[2]

			if node_1:
				n_text = node_1.get("text", "")
				n_label = node_1.get("label", "Entity")
				if n_text and n_text not in entities_map:
					entities_map[n_text] = {"text": n_text, "label": n_label}

			if relation and node_2:
				m_text = node_2.get("text", "")
				m_label = node_2.get("label", "Entity")
				if m_text and m_text not in entities_map:
					entities_map[m_text] = {"text": m_text, "label": m_label}
				src = node_1.get("text", "") if node_1 else ""
				tgt = m_text
				pred = relation.get("predicate", "RELATES_TO")
				prop = relation.get("proposed_by", "PENDING_FUTURE_MODEL")
				acc = relation.get("patient_acceptance", "PENDING_FUTURE_MODEL")
				rel_key = (src, pred, tgt)
				if src and tgt and rel_key not in seen_relation_keys:
					seen_relation_keys.add(rel_key)
					relations.append({
						"source": src,
						"predicate": pred,
						"target": tgt,
						"proposed_by": prop,
						"patient_acceptance": acc,
					})

		entities = list(entities_map.values())
		return {"entities": entities, "relations": relations}
	except Exception as e:
		print(f"Failed to export graph for patient {patient_id}: {e}")
		return {"entities": [], "relations": []}


@app.get("/api/graph/{patient_id}")
async def get_patient_graph(patient_id: str):
	"""Returns the knowledge graph for a patient from LadybugDB."""
	return export_graph_from_db(patient_id)


@app.post("/api/knowledge-graph")
async def create_knowledge_graph_job(request: KnowledgeGraphRequest, background_tasks: BackgroundTasks):
	if not request.transcript_payload.transcript:
		raise HTTPException(status_code=400, detail="Transcript payload must include at least one transcript item.")

	job_id = str(uuid.uuid4())
	job_store[job_id] = {
		"status": "processing",
		"result": None,
		"error": None,
	}
	background_tasks.add_task(process_knowledge_graph_job, job_id, request.model_dump())
	return {"message": "Knowledge graph extraction started.", "job_id": job_id}


@app.get("/api/jobs/{job_id}")
async def get_job_status(job_id: str):
	if job_id not in job_store:
		raise HTTPException(status_code=404, detail="Job not found.")

	job = job_store[job_id]
	if job["status"] == "processing":
		return {"status": "processing"}
	if job["status"] == "failed":
		return {"status": "failed", "error": job["error"]}
	return {"status": "completed", "result": job["result"]}


if __name__ == "__main__":
	uvicorn.run(app, host="0.0.0.0", port=8086)
