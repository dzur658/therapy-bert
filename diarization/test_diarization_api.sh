#!/bin/bash

# --- Configuration ---
# Update this to point to your actual demo file
FILE_PATH="$HOME/ai_projects/new_jh_test.wav" 
API_URL="http://127.0.0.1:8085"

# 1. The Drop-Off
echo "1. Uploading $FILE_PATH to the API..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/api/transcribe" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "audio_file=@$FILE_PATH")

# Extract the job_id using a Python one-liner
JOB_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('job_id', ''))")

if [ -z "$JOB_ID" ]; then
    echo "Upload failed! Server response:"
    echo "$UPLOAD_RESPONSE"
    exit 1
fi

echo "Success! Received Pager/Job ID: $JOB_ID"
echo "2. Polling the server every 5 seconds..."

# 2. The Polling Loop
STATUS="processing"
while [ "$STATUS" == "processing" ]; do
    # Sleep mimics the React setInterval timer
    sleep 5 
    
    # Check the status
    POLL_RESPONSE=$(curl -s -X GET "$API_URL/api/jobs/$JOB_ID" -H "accept: application/json")
    
    # Extract just the status string to evaluate the while loop
    STATUS=$(echo "$POLL_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', 'unknown'))")
    
    echo "[$(date +'%H:%M:%S')] Checked API... Status: $STATUS"
done

# 3. The Result
echo "--------------------------------------------------"
if [ "$STATUS" == "completed" ]; then
    echo "3. Transcription Complete! Here is the JSON payload:"
    # Use Python's built-in json tool to pretty-print the final output
    echo "$POLL_RESPONSE" | python3 -m json.tool
else
    echo "Job failed or encountered an error:"
    echo "$POLL_RESPONSE" | python3 -m json.tool
fi