#!/bin/bash

# Configuration
API_URL="http://localhost:8086"
PAYLOAD_FILE="demo_transcript_payload.json"

echo "======================================================"
echo "🧠 Knowledge Graph End-to-End Test (Powered by jq)"
echo "======================================================"

# 1. Create the simulated patient transcript
cat <<EOF > $PAYLOAD_FILE
{
  "patient_id": "demo-patient-001",
  "transcript_payload": {
    "transcript": [
      {
        "speaker": "Therapist",
        "text": "How have you been feeling since our last session?"
      },
      {
        "speaker": "Patient",
        "text": "My anxiety has been getting worse since the calls from my ex-husband started again. Also, I avoid crowded stores because the flashing lights can trigger a panic attack."
      }
    ]
  },
  "inference_config": {
    "max_context_tokens": 8192,
    "window_overlap_tokens": 1000,
    "relation_batch_size": 8
  }
}
EOF

echo "Submitting transcript to local ModernBERT pipeline..."

# 2. Submit the POST request
RESPONSE=$(curl -s -X POST "$API_URL/api/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d @$PAYLOAD_FILE)

# 3. Extract the job_id using jq (-r gives raw text without quotes)
JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id // empty')

if [ -z "$JOB_ID" ]; then
    echo "❌ Failed to queue the job. API responded with:"
    echo "$RESPONSE" | jq .
    rm $PAYLOAD_FILE
    exit 1
fi

echo "✅ Job successfully queued! Job ID: $JOB_ID"
echo -n "Polling background task for completion"

# 4. Polling Loop
STATUS="processing"
while [ "$STATUS" == "processing" ]; do
    sleep 2
    echo -n "."
    POLL_RESPONSE=$(curl -s -X GET "$API_URL/api/jobs/$JOB_ID")
    STATUS=$(echo "$POLL_RESPONSE" | jq -r '.status // "failed"')
done

echo ""
echo "======================================================"

# 5. Output the pretty-printed result
if [ "$STATUS" == "completed" ]; then
    echo "🎉 Graph Compilation Complete!"
    echo "Final Knowledge Graph Payload:"
    echo "$POLL_RESPONSE" | jq .
else
    echo "🔥 Job Failed!"
    echo "Error Details:"
    echo "$POLL_RESPONSE" | jq .
fi

# Cleanup
rm $PAYLOAD_FILE