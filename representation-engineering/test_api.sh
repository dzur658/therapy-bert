#!/bin/bash

API_URL="http://localhost:8086/analyze"
REVEAL=${1:-"experiencing anxiety because"}

# We use a Heredoc (cat <<EOF) to safely format the multi-line JSON payload 
# without getting trapped in a nightmare of escaping quotes.
PAYLOAD=$(cat <<EOF
{
  "transcript": "I mean, I'm fine. I'm completely fine. Everything is just... fine. I don't even know why my wife insisted I come to this session. I have a great job, a nice house, we go on vacations. I check all the boxes. If I'm a little quiet after work, it's just because I'm tired, not because I'm avoiding her or 'shutting down' like she claims.",
  "reveal": "$REVEAL"
}
EOF
)

echo "======================================================"
echo "🧠 Firing Payload at Rep-Eng API..."
echo "======================================================"
echo "Endpoint: $API_URL"
echo "------------------------------------------------------"
echo "Payload:"
echo "$PAYLOAD" | python3 -m json.tool
echo "------------------------------------------------------"
echo "Waiting for Qwen to process (this might take a minute on CPU)..."

# -s: Silent mode (hides the progress bar)
# -X POST: Explicitly tells the server we are sending data, not just reading
# -H: Sets the header so FastAPI knows to parse the body as JSON
# -d: The actual payload
# | python3 -m json.tool: We pipe the raw output into Python's built-in JSON formatter 
# so it doesn't print as one giant, unreadable wall of text.

curl -s -X POST "$API_URL" \
     -H "Content-Type: application/json" \
     -d "$PAYLOAD" | python3 -m json.tool

echo -e "\n======================================================"
echo "✅ Request Complete!"