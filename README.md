# TherapyBERT

> **Clinical knowledge graph extraction from therapy sessions — end-to-end, on-device, GPU-accelerated.**

Fine-tunes [ModernBERT-large](https://huggingface.co/answerdotai/ModernBERT-large) to extract structured clinical knowledge from therapy transcripts, stores it in a per-patient graph database, and surfaces it through a desktop GUI and a graph-grounded chat interface — all running locally with no PHI leaving the machine.

---

## What It Does

Raw therapy audio goes in. A structured, queryable clinical knowledge graph comes out.

```
  🎙  Audio Recording
        │
        ▼
  ┌─────────────────────────────┐
  │   Diarization Pipeline      │  distil-whisper + pyannote
  │   Speaker ID + Transcript   │  word-level timestamps
  └─────────────┬───────────────┘
                │
                ▼
  ┌─────────────────────────────┐
  │   Knowledge Graph API       │  ModernBERT-large backbone
  │                             │
  │   ┌──────────┐              │  NER — ModernBERT + CRF
  │   │   NER    │──entities──► │  7 clinical entity types
  │   └──────────┘              │
  │   ┌──────────┐              │  RE  — ModernBERT + Entity Pooling
  │   │    RE    │──relations──►│  7 relation predicates
  │   └──────────┘              │  + epistemic metadata
  └─────────────┬───────────────┘
                │
                ▼
  ┌─────────────────────────────┐
  │   LadybugDB (Graph Store)   │  per-patient .lbug files
  │   Nodes + Edges + Meta      │  Cypher-style query API
  └─────────────┬───────────────┘
                │
        ┌───────┴────────┐
        ▼                ▼
  ┌──────────┐    ┌──────────────────┐
  │ Graph    │    │  Graph RAG Chat  │  clinician Q&A grounded
  │   GUI    │    │      API         │  in the patient's graph
  └──────────┘    └──────────────────┘
  Tauri + React
```

---

## Clinical Entities Extracted

| Entity | Examples |
|---|---|
| `Symptom` | panic attacks, insomnia, dissociation |
| `Trigger` | crowded spaces, phone calls, confrontation |
| `Emotion` | anxious, overwhelmed, ashamed |
| `Person` | my father, my partner, my boss |
| `Coping_Mechanism` | breathing exercises, alcohol, journaling |
| `Life_Event` | childhood trauma, divorce, job loss |
| `Behavior` | avoidance, outbursts, self-isolation |

## Relation Predicates

`CAUSES` · `WORSENS` · `IMPROVES` · `RELATES_TO` · `EXPERIENCES` · `TRIGGERS` · `NONE`

Every extracted relation carries **epistemic metadata**: who proposed it (`Patient` / `Therapist`) and how the patient responded (`Affirmed` / `Denied` / `Avoided` / `Realized_Later`).

---

## Architecture

### NER — `ModernBERT_CRF`

ModernBERT-large (8192-token context, bfloat16, SDPA attention) with a linear emission layer feeding a **Conditional Random Field** decoder. The CRF transition matrix is pre-initialized to hard-enforce IOB grammar — `I-X` tokens can only follow `B-X` or `I-X`, not other entity types and not the start of a sequence.

Two-phase training:
1. **Phase 1** — Backbone frozen, CRF head only (1 epoch, lr=1e-3). Stabilizes random emissions before any gradient flows into the pretrained weights.
2. **Phase 2** — Full fine-tune with early stopping (lr=2e-6, patience=2). Best checkpoint selected by eval loss.

### RE — `ModernBERT_Entity_Pooling_RE`

Four special tokens (`[E1]`, `[/E1]`, `[E2]`, `[/E2]`) are injected around entity spans in the input. Their embeddings are trained from scratch in Phase 1 while the backbone is frozen; Phase 2 fine-tunes everything together. At inference, the hidden states at each entity's marker positions are mean-pooled and concatenated (2048-dim) for relation classification.

### Knowledge Graph API

Sliding-window chunking (default 4096 spaCy tokens, 1000-token overlap) handles transcripts of arbitrary length. A **center-weighted proximity score** resolves entity and relation duplicates across window boundaries — spans closer to the window center are preferred, preventing boundary artifacts from biasing the graph.

---

## Repository Layout

```
therapy-bert/
├── knowledge_graph_api.py          # FastAPI service — NER + RE → LadybugDB (port 8086)
├── graph_rag_api.py                # Graph-grounded chat API (port 8091)
├── ner_crf_layer.py                # ModernBERT_CRF model definition
├── modern_bert_re_layers.py        # ModernBERT_Entity_Pooling_RE model definition
├── modern_bert_ner_trainer.py      # NER training (2-phase)
├── modern_bert_re_trainer.py       # RE training (2-phase)
├── ner_inference_pipeline.py       # NER inference
├── re_inference_pipeline.py        # RE inference
├── ladybug_db/
│   └── db_manager.py              # Graph database (Cypher-style API)
├── patients/                       # Per-patient .lbug graph files
├── synthetic-data-gen/
│   ├── generator.py               # LLM transcript generation (3,000 sessions)
│   ├── entity_shard_generator.py  # LLM entity annotation pass
│   ├── re_shard_generator.py      # LLM relation annotation pass
│   ├── iob_labelling.py           # Span → BIO tag conversion
│   ├── create_splits.py           # Train / val / test splits
│   ├── validation.py              # Pydantic schemas (entity + relation types)
│   └── config.py                  # Pipeline configuration
├── diarization/
│   ├── diarization_engine.py      # Whisper + Pyannote diarization
│   └── diarization_api.py         # FastAPI wrapper (port 8085)
├── representation-engineering/    # Experimental: Qwen3 subtext shadow vectors
├── tauri-app/therapy-bert-gui/    # Desktop GUI — Tauri (Rust) + React/TS/Vite
├── therapy-modernbert-ner-final/  # Trained NER model (~1.5 GB)
├── therapy-modernbert-re-final/   # Trained RE model (~790 MB)
└── requirements.txt
```

---

## Models

| Model | Role |
|---|---|
| `answerdotai/ModernBERT-large` | NER + RE backbone (8192-token context, bfloat16) |
| `distil-whisper/distil-large-v3.5-ct2` | Speech recognition with word-level timestamps |
| `pyannote/speaker-diarization-community-1` | Speaker diarization |
| `Qwen/Qwen3-0.6B-Base` | Experimental subtext representation engineering |
| Local LLM (via Open AI Responses API) | Synthetic data generation |

---

## Getting Started

### Prerequisites

```bash
# Python 3.10+
pip install -r requirements.txt

# For the desktop GUI (requires Rust + Node)
cd tauri-app/therapy-bert-gui
npm install
```

### Run the Services

**Standalone dev (top-level scripts):**
Top level APIs are dev implementations, packaged versions in `./tauri-app/therapy-bert-gui/backend` are bundled with the Tauri app.

```bash
# Diarization API (port 8085)
python diarization/diarization_api.py

# Knowledge Graph API — NER + RE extraction (port 8086)
python knowledge_graph_api.py

# Graph RAG Chat API (port 8091)
python graph_rag_api.py

# SQLite server — patient & session storage (port 8088)
python tauri-app/therapy-bert-gui/backend/diarization/sqlite_helper_api.py

# Representation Engineering API (port 8087)
python tauri-app/therapy-bert-gui/backend/representation-engineering/representation_extraction_api.py
```

When running the full desktop app, start all five services (diarization, knowledge graph, graph RAG, SQLite, representation engineering) plus the GUI.

### Extract a Knowledge Graph

```bash
curl -X POST http://localhost:8086/api/knowledge-graph \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "001",
    "transcript_payload": {
      "transcript": [
        {"speaker": "Patient", "text": "I have been more anxious lately."},
        {"speaker": "Therapist", "text": "What seems to trigger it?"},
        {"speaker": "Patient", "text": "Crowds. Any time I am in a crowd I get a panic attack."}
      ]
    },
    "inference_config": {
      "max_context_tokens": 4096,
      "window_overlap_tokens": 1000,
      "relation_batch_size": 8
    }
  }'
```

Poll for results:

```bash
curl http://localhost:8086/api/jobs/<job_id>
```

### Train the Models

```bash
# NER — ModernBERT + CRF
python modern_bert_ner_trainer.py

# RE — ModernBERT + Entity Pooling
python modern_bert_re_trainer.py
```

### Synthetic Data Generation

```bash
# 1. Generate therapy transcripts
python synthetic-data-gen/generator.py

# 2. Entity annotation pass
python synthetic-data-gen/entity_shard_generator.py

# 3. Relation annotation pass
python synthetic-data-gen/re_shard_generator.py

# 4. BIO tag conversion
python synthetic-data-gen/iob_labelling.py

# 5. Create train/val/test splits
python synthetic-data-gen/create_splits.py
```

### Desktop GUI

```bash
cd tauri-app/therapy-bert-gui
npm run tauri dev
```

---

## Experimental: Representation Engineering

`representation-engineering/` explores **shadow vectors** — the difference in hidden states between a literal surface reading and the clinical subtext of a patient's statement — using Qwen3-0.6B-Base. The goal is to steer the model toward surfacing what the patient is communicating *beneath* the words, without any supervised signal.

---

## Design Principles

- **Fully on-device.** No transcript, patient ID, or graph data is ever sent to an external API. Everything runs locally.
- **Long-context by default.** ModernBERT's 8192-token context window means an entire session can often be processed in a single forward pass if compute resources allow.
- **Epistemic metadata.** Relations aren't just edges — they carry who proposed the connection and whether the patient accepted, denied, or avoided it (coming soon). This is clinically meaningful signal that most KG systems discard.
- **Schema-first.** Entity and relation types are defined once in `synthetic-data-gen/validation.py` and referenced everywhere — training data, inference, and the graph DB — so a schema change propagates cleanly.
- **Sliding windows, not truncation.** When a transcript exceeds the model's context, overlapping windows are used with center-weighted deduplication rather than silently dropping content.
