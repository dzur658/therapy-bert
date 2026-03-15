import asyncio
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from typing import Dict, List
import uvicorn

import real_ladybug as lbug

# Resolve path to backend/kg/patients (graph_rag_api.py lives in backend/basic-graph-rag/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_PATIENTS_DIR = _BACKEND_DIR / "kg" / "patients"

app = FastAPI(title="Therapy Knowledge Graph API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Point to your local LiteLLM / Llama.cpp instance
aclient = AsyncOpenAI(api_key="sk-local-demo", base_url="http://192.168.1.110:8090/v1")

# In-memory session store: { session_id: [ {"role": "...", "content": "..."}, ... ] }
# Note: For a production app, this moves to Redis. For a demo, a Python dict is perfect.
chat_sessions: Dict[str, List[dict]] = {}

class ChatRequest(BaseModel):
    session_id: str
    patient_id: str
    message: str
    patient_name: str = "Patient"  # Used in system prompt for personalized responses
    graph_context: str | None = None  # Optional: frontend passes the graph it's already displaying

def _read_graph_context_sync(patient_id: str) -> str:
    """Synchronous DB read — run via run_in_executor to avoid blocking the event loop."""
    db_path = _PATIENTS_DIR / f"patient_{patient_id}_graph.lbug"
    if not db_path.exists():
        print(f"No graph DB found for patient {patient_id} at {db_path}")
        return "No graph context available."

    try:
        db = lbug.Database(str(db_path))
        conn = lbug.Connection(db)

        query = """
        MATCH (n)
        OPTIONAL MATCH (n)-[r]->(m)
        RETURN n, r, m
        """
        results = conn.execute(query)

        context_lines = set()

        while results.has_next():
            row = results.get_next()
            node_1 = row[0]
            relation = row[1]
            node_2 = row[2]

            if not node_1:
                continue

            n_text = node_1.get("text", "")
            n_label = node_1.get("label", "Entity")

            if not n_text:
                continue

            if relation and node_2:
                m_text = node_2.get("text", "")
                m_label = node_2.get("label", "Entity")
                pred = relation.get("predicate", "RELATES_TO")
                if m_text:
                    context_lines.add(f"[{n_label}] {n_text} -> {pred} -> [{m_label}] {m_text}")
            else:
                context_lines.add(f"[{n_label}] {n_text} (Isolated)")

        print(f"Loaded {len(context_lines)} context lines for patient {patient_id}")
        return "\n".join(sorted(list(context_lines)))
    except Exception as e:
        print(f"Failed to fetch graph for {patient_id}: {e}")
        return "No graph context available."

async def fetch_dynamic_graph_context(patient_id: str) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _read_graph_context_sync, patient_id)

@app.post("/api/chat")
async def chat_with_graph(request: ChatRequest):
    # 1. Initialize the session if it doesn't exist
    if request.session_id not in chat_sessions:
        print(f"Initializing new chat session: {request.session_id} for patient: {request.patient_id}")

        # Use graph_context from frontend (already-loaded graph) if provided; else read from DB
        if request.graph_context:
            graph_context = request.graph_context
            print(f"Using graph context from frontend ({len(graph_context)} chars)")
        else:
            # tries to read from DB but will probably be blocked due to the sync call
            graph_context = await fetch_dynamic_graph_context(request.patient_id)
        
        system_prompt = f"""You are an elite clinical AI assistant analyzing {request.patient_name}'s Knowledge Graph. 
Answer the user's questions based ONLY on the graph context provided below. 
Do not hallucinate external clinical facts. Be concise and professional.
When referring to the patient, use their name: {request.patient_name}.

CRITICAL RULES:
1. You may only connect two concepts if there is a direct arrow (->) between them in the text.
2. DO NOT attribute an isolated node to a specific person or entity unless explicitly linked.
3. If the graph does not show a direct cause for a feeling, say "The graph does not specify the exact cause."

PATIENT GRAPH CONTEXT:
<knowledge_graph_shards>
{graph_context}
</knowledge_graph_shards>
"""
        print(f"System prompt for session {request.session_id}:\n{system_prompt}\n{'-'*50}")

        chat_sessions[request.session_id] = [{"role": "system", "content": system_prompt}]

    # 2. Append the new user message to the history
    chat_sessions[request.session_id].append({"role": "user", "content": request.message})

    # 3. Create the streaming generator
    async def generate_tokens():
        full_response = ""
        try:
            response = await aclient.chat.completions.create(
                model="MiniMax M 2.5", # Update to match your litellm config
                messages=chat_sessions[request.session_id],
                stream=True,
            )
            async for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    token = chunk.choices[0].delta.content
                    full_response += token  # Capture the token in memory
                    yield token             # Stream the token to React
                    
        finally:
            # 4. The Magic Trick: When the stream finishes (or disconnects), 
            # save the complete assembled string to the session history.
            if full_response.strip():
                chat_sessions[request.session_id].append({"role": "assistant", "content": full_response})

    return StreamingResponse(generate_tokens(), media_type="text/plain")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8091)