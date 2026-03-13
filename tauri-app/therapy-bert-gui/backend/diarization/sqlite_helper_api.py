import sqlite3
import json
from pathlib import Path
from platformdirs import user_data_dir
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI(title="Therapy BERT Database Service")

# --- PATH CONFIGURATION (The AppData safe-zone) ---
APP_NAME = "TherapyBERT"
APP_AUTHOR = "dzur658" 
DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
DATA_DIR.mkdir(parents=True, exist_ok=True)

SQLITE_PATH = DATA_DIR / "therapy_transcripts.sqlite"

# --- DB INITIALIZATION ---
sql_conn = sqlite3.connect(str(SQLITE_PATH), check_same_thread=False)

def init_db():
    """Ensures the tables exist the first time a therapist launches the app."""
    cursor = sql_conn.cursor()
    
    # Create Patients Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS patients (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create Sessions Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            patient_id TEXT,
            audio_file_path TEXT,
            transcript_json TEXT, 
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES patients (id)
        )
    ''')
    sql_conn.commit()

# Run the initialization immediately when the API starts
init_db()

# --- PYDANTIC MODELS (The Molds) ---
class SessionData(BaseModel):
    session_id: str
    patient_id: str
    audio_file_path: str
    transcript_data: Dict[str, Any]

# --- THE ENDPOINTS ---
@app.post("/db/sqlite/sessions")
async def save_session_transcript(payload: SessionData):
    """Saves the raw transcript array and metadata to SQLite."""
    try:
        cursor = sql_conn.cursor()
        cursor.execute(
            """INSERT INTO sessions (id, patient_id, audio_file_path, transcript_json) 
               VALUES (?, ?, ?, ?)""",
            (
                payload.session_id, 
                payload.patient_id, 
                payload.audio_file_path, 
                json.dumps(payload.transcript_data)
            )
        )
        sql_conn.commit()
        return {"status": "success", "message": "Transcript saved to SQLite"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/db/sqlite/sessions/{patient_id}")
async def get_patient_sessions(patient_id: str):
    """Fetches a patient's historical transcripts for the React UI."""
    cursor = sql_conn.cursor()
    cursor.execute(
        "SELECT id, created_at, transcript_json FROM sessions WHERE patient_id = ? ORDER BY created_at DESC", 
        (patient_id,)
    )
    rows = cursor.fetchall()
    
    sessions = [
        {"session_id": row[0], "date": row[1], "transcript": json.loads(row[2])} 
        for row in rows
    ]
    return {"status": "success", "data": sessions}