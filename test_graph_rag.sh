#!/bin/bash

API_URL="http://127.0.0.1:8091/api/chat"
# Generate a unique session ID for this specific test run
SESSION_ID="cli-test-session-$(date +%s)"
PATIENT_ID="gtc-demo-enmeshment-002"

echo "======================================================"
echo "🧠 Testing Graph RAG Chat API (Streaming & State)"
echo "======================================================"
echo "Session ID: $SESSION_ID"
echo "Patient ID: $PATIENT_ID"
echo "------------------------------------------------------"

# --- Turn 1: Primary Question ---
Q1="How does the patient feel about Sarah?"
echo -e "🧑‍⚕️ User: $Q1"
echo -n "🤖 AI: "

# We use -N (--no-buffer) to see the streaming effect in the terminal
curl -s -N -X POST "$API_URL" \
     -H "Content-Type: application/json" \
     -d '{
           "session_id": "'"$SESSION_ID"'",
           "patient_id": "'"$PATIENT_ID"'",
           "message": "'"$Q1"'"
         }'

echo -e "\n\n------------------------------------------------------"
sleep 2 # Pause briefly to simulate the user reading and typing

# --- Turn 2: Follow-up Question (Testing Memory) ---
# Notice we don't say "panic attacks" here. The AI has to remember it from Turn 1.
Q2="Why might the patient feel this way about Sarah?"
echo -e "🧑‍⚕️ User: $Q2"
echo -n "🤖 AI: "

curl -s -N -X POST "$API_URL" \
     -H "Content-Type: application/json" \
     -d '{
           "session_id": "'"$SESSION_ID"'",
           "patient_id": "'"$PATIENT_ID"'",
           "message": "'"$Q2"'"
         }'

echo -e "\n\n======================================================"
echo "✅ Chat Test Complete!"