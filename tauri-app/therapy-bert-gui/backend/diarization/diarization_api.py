from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import shutil
import os
import tempfile
import uuid
from typing import Dict

# Import your custom pipeline
from diarization_engine import DiarizationEngine 

app = FastAPI(title="Therapy Diarization API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. The Status Board: An in-memory dictionary to track all active tasks
job_store: Dict[str, dict] = {}


# 2. The Background Worker: This function runs independently of the web requests
def process_audio_task(job_id: str, file_path: str, temp_dir: str):
    """Handles the heavy AI lifting and cleans up the disk afterward."""
    try:
        print(f"[{job_id}] Starting background processing...")

        print("Loading AI Models into memory...")
        engine = DiarizationEngine() 
        print("Models loaded and ready.")

        transcript_payload = engine.diarize_and_transcribe(file_path)
        
        # Update the status board with the final payload
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["result"] = transcript_payload
        print(f"[{job_id}] Processing complete!")
        
    except Exception as e:
        print(f"[{job_id}] Error: {str(e)}")
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = str(e)
        
    finally:
        # 3. Housekeeping: Delete the temporary folder ONLY after the AI is done reading it
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"[{job_id}] Cleaned up temporary files.")


# 4. The Drop-Off Endpoint: Catches the file and gives React a pager
@app.post("/api/transcribe")
async def upload_and_start_transcription(
    background_tasks: BackgroundTasks, 
    audio_file: UploadFile = File(...)
):
    if not audio_file.filename.endswith('.wav'):
        raise HTTPException(status_code=400, detail="Only .wav files are supported.")
    
    # Generate a unique "pager" ID for this specific audio file
    job_id = str(uuid.uuid4())
    
    # Register the job on the status board
    job_store[job_id] = {"status": "processing", "result": None}

    # Save the file to disk safely
    temp_dir = tempfile.mkdtemp()
    temp_file_path = os.path.join(temp_dir, audio_file.filename)

    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(audio_file.file, buffer)
        
    # Hand the heavy lifting off to the background worker
    background_tasks.add_task(process_audio_task, job_id, temp_file_path, temp_dir)
    
    # Immediately return the pager ID to React (usually takes < 1 second)
    return {"message": "Audio received. Processing started.", "job_id": job_id}


# 5. The Polling Endpoint: React checks this to see if the food is ready
@app.get("/api/jobs/{job_id}")
async def check_job_status(job_id: str):
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found.")
        
    job_data = job_store[job_id]
    
    # If it's still running, just tell React to keep waiting
    if job_data["status"] == "processing":
        return {"status": "processing"}
        
    # If it failed, tell React so it can show an error message
    if job_data["status"] == "failed":
        return {"status": "failed", "error": job_data.get("error")}
        
    # If it's done, hand over the goods!
    if job_data["status"] == "completed":
        return {"status": "completed", "transcript": job_data["result"]}
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8085)