import sqlite3
import json
import uuid
import uvicorn
from pathlib import Path
from platformdirs import user_data_dir
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

app = FastAPI(title="Therapy BERT Database Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PATH CONFIGURATION (The AppData safe-zone) ---
APP_NAME = "TherapyBERT"
APP_AUTHOR = "dzur658"
DATA_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
DATA_DIR.mkdir(parents=True, exist_ok=True)

SQLITE_PATH = DATA_DIR / "therapy_transcripts.sqlite"

# --- DB INITIALIZATION ---
sql_conn = sqlite3.connect(str(SQLITE_PATH), check_same_thread=False)
# Enable WAL mode to prevent "Database is Locked" errors during demo
sql_conn.execute("PRAGMA journal_mode=WAL")

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


class CreatePatientData(BaseModel):
    name: str

# --- PATIENT ENDPOINTS ---
@app.get("/db/sqlite/patients")
async def list_patients():
    """Lists all patients with session count and last session date."""
    cursor = sql_conn.cursor()
    cursor.execute("""
        SELECT p.id, p.name, p.created_at,
               COUNT(s.id) AS session_count,
               MAX(s.created_at) AS last_session
        FROM patients p
        LEFT JOIN sessions s ON s.patient_id = p.id
        GROUP BY p.id, p.name, p.created_at
        ORDER BY p.created_at DESC
    """)
    rows = cursor.fetchall()
    patients = [
        {
            "id": row[0],
            "name": row[1],
            "created_at": row[2],
            "session_count": row[3] or 0,
            "last_session": row[4],
        }
        for row in rows
    ]
    return {"status": "success", "data": patients}


@app.post("/db/sqlite/patients")
async def create_patient(payload: CreatePatientData):
    """Creates a new patient."""
    patient_id = str(uuid.uuid4())
    try:
        cursor = sql_conn.cursor()
        cursor.execute(
            "INSERT INTO patients (id, name) VALUES (?, ?)",
            (patient_id, payload.name.strip()),
        )
        sql_conn.commit()
        return {"status": "success", "data": {"id": patient_id, "name": payload.name.strip()}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/db/sqlite/patients/{patient_id}")
async def delete_patient(patient_id: str):
    """Deletes a patient and all their sessions."""
    try:
        cursor = sql_conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE patient_id = ?", (patient_id,))
        cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        deleted = cursor.rowcount
        sql_conn.commit()
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Patient not found")
        return {"status": "success", "message": "Patient deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- SESSION ENDPOINTS ---
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


class UpdateSessionData(BaseModel):
    transcript_data: Dict[str, Any]


@app.put("/db/sqlite/sessions/{session_id}")
async def update_session_transcript(session_id: str, payload: UpdateSessionData):
    """Updates the transcript JSON for an existing session."""
    try:
        cursor = sql_conn.cursor()
        cursor.execute(
            "UPDATE sessions SET transcript_json = ? WHERE id = ?",
            (json.dumps(payload.transcript_data), session_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        sql_conn.commit()
        return {"status": "success", "message": "Transcript updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/db/sqlite/sessions/{session_id}")
async def delete_session(session_id: str):
    """Deletes a session transcript from the database."""
    try:
        cursor = sql_conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Session not found")
        sql_conn.commit()
        return {"status": "success", "message": "Session deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8088)