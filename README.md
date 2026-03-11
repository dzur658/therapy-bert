# therapy-bert
The code repository for making therapy bert

## Knowledge Graph API

`knowledge_graph_api.py` exposes a FastAPI service that accepts the diarization transcript payload, reconstructs a speaker-labeled transcript, runs NER and RE inference, and writes the extracted graph into the local Ladybug database.

Run the API:

```bash
python knowledge_graph_api.py
```

Start a graph extraction job:

```bash
curl -X POST http://localhost:8086/api/knowledge-graph \
	-H "Content-Type: application/json" \
	-d '{
		"patient_id": "001",
		"transcript_payload": {
			"transcript": [
				{"speaker": "Patient", "text": "I have been more anxious lately."},
				{"speaker": "Therapist", "text": "What seems to trigger it?"}
			]
		},
		"inference_config": {
			"max_context_tokens": 8192,
			"window_overlap_tokens": 1000,
			"relation_batch_size": 8
		}
	}'
```

Poll job status:

```bash
curl http://localhost:8086/api/jobs/<job_id>
```

Notes:

- Speaker labels are used exactly as provided by the caller. The frontend is responsible for replacing diarization speaker IDs with the therapist-selected roles before calling the API.
- If the reconstructed transcript exceeds `8192` spaCy tokens, the API uses overlapping sliding windows with a default overlap of `1000` tokens.
- Entity and relation label allow-lists are loaded directly from `synthetic-data-gen/validation.py` for faster schema prototyping.
- `proposed_by` and `patient_acceptance` are currently written with placeholder values so DB insertion works until the future pass model is added.
