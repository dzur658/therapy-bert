#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8086}"
MAX_POLLS="${MAX_POLLS:-60}"
SLEEP_SECONDS="${SLEEP_SECONDS:-2}"

echo "Submitting knowledge graph job to ${API_URL}..."

create_response="$(curl -sS -X POST "${API_URL}/api/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "test_patient_kg_api_001",
    "transcript_payload": {
      "transcript": [
        {
          "speaker": "Patient",
          "text": "Lately I have been waking up with my chest tight and I keep replaying the car accident from last winter."
        },
        {
          "speaker": "Therapist",
          "text": "When the memories of the accident come up, what tends to happen in your body and what do you do next?"
        },
        {
          "speaker": "Patient",
          "text": "My heart races, I feel panic, and I avoid driving on the highway whenever I can."
        },
        {
          "speaker": "Therapist",
          "text": "Does avoiding the highway make the panic feel better in the moment, even if it keeps the fear going overall?"
        },
        {
          "speaker": "Patient",
          "text": "Yes, avoiding it calms me down for a bit, but then I feel ashamed and even more anxious the next day."
        },
        {
          "speaker": "Therapist",
          "text": "You also mentioned arguing more with your sister after poor sleep. Tell me about that connection."
        },
        {
          "speaker": "Patient",
          "text": "If I sleep badly, I get irritable, I snap at my sister, and then I isolate in my room because I feel guilty."
        },
        {
          "speaker": "Therapist",
          "text": "What has helped at least a little when the panic or irritability starts building?"
        },
        {
          "speaker": "Patient",
          "text": "Breathing exercises and texting my friend Marcus help sometimes, but loud traffic still triggers me."
        }
      ]
    },
    "inference_config": {
      "max_context_tokens": 8192,
      "window_overlap_tokens": 1000,
      "relation_batch_size": 8
    }
  }')"

echo "Create response:"
echo "${create_response}"

job_id="$(CREATE_RESPONSE="${create_response}" python - <<'PY'
import json
import os

payload = json.loads(os.environ["CREATE_RESPONSE"])
print(payload["job_id"])
PY
)"

if [[ -z "${job_id}" ]]; then
  echo "Failed to extract job_id from API response."
  exit 1
fi

echo "Polling job ${job_id}..."

for ((attempt=1; attempt<=MAX_POLLS; attempt++)); do
  status_response="$(curl -sS "${API_URL}/api/jobs/${job_id}")"
  status="$(STATUS_RESPONSE="${status_response}" python - <<'PY'
import json
import os

payload = json.loads(os.environ["STATUS_RESPONSE"])
print(payload["status"])
PY
)"

  echo "Poll ${attempt}/${MAX_POLLS}: ${status}"

  if [[ "${status}" == "completed" ]]; then
    echo "Job completed successfully."
    echo "${status_response}" | python -m json.tool
    exit 0
  fi

  if [[ "${status}" == "failed" ]]; then
    echo "Job failed."
    echo "${status_response}" | python -m json.tool
    exit 1
  fi

  sleep "${SLEEP_SECONDS}"
done

echo "Timed out waiting for job completion."
exit 1