from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import torch

import jinja2 as j2

# Import the engine
from hidden_state_extraction import SubtextEngine 

app = FastAPI(title="Subtext Diagnostic API")

# 1. CORS Setup (The Bouncer)
# This explicitly allows your local React dev server (usually localhost:3000 or 5173) 
# to talk to this Python server without the browser throwing a CORS error.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Change to ["http://localhost:3000"] in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Global Engine Initialization
engine = None
COURT_REPORTER_MATRIX = j2.Template("""
        Convert the subjective transcript into a sterile, physical, and objective Court Reporter fact.

        Transcript: "He is a complete idiot for doing that behind my back! I hate him!"
        Fact: The subject stated that a secondary individual took an action without their prior knowledge.

        Transcript: "Oh, you know, just another day in paradise! My car broke down, but hey, I didn't get hit by a bus!"
        Fact: The subject experienced a mechanical vehicle failure and remained physically uninjured.

        Transcript: "I don't know... It doesn't really matter what I do, does it? I'll just sit here and see what happens."
        Fact: The subject indicated a lack of preference for future actions and stated they will wait.

        Transcript: "I haven't slept in three days because I'm finally figuring out the algorithm, it's all connected, I just need more coffee!"
        Fact: The subject reported being awake for 72 hours working on a mathematical problem and expressed a need for caffeine.

        Transcript: "Sure, whatever. I guess I'll just keep doing exactly what she says. It's fine. I'm used to it."
        Fact: The subject agreed to comply with the instructions provided by a female individual.

        Transcript: "I can't go back in there. My chest is tight, I can't breathe, everyone is just staring at me waiting for me to fail."
        Fact: The subject expressed an unwillingness to re-enter the room, reported respiratory physical sensations, and stated others were observing them.

        Transcript: "It feels like a hole in my chest. I keep waiting for him to walk through the door, but he never does. It's so quiet."
        Fact: The subject described a physical sensation in their chest and noted the continued absence of a male individual in their environment.

        Transcript: "No, I'm not mad he forgot our anniversary. His startup is in a critical phase. Work is important. It's a logical prioritization."
        Fact: The subject stated their partner missed an anniversary due to professional commitments and acknowledged the logistical reasoning.

        Transcript: "I'm such a monster. I shouldn't have yelled at the kids like that, I ruined the whole weekend."
        Fact: The subject recalled raising their voice at children and stated this action negatively impacted the weekend schedule.

        Transcript: "There's just too much! The emails, the deadlines, the house is a mess, I'm drowning in all of this!"
        Fact: The subject listed multiple uncompleted tasks, including digital correspondence, professional deadlines, and household maintenance.

        Transcript: "They keep whispering when I walk by. I know they're trying to get me fired, I can see it in their eyes."
        Fact: The subject reported observing colleagues speaking quietly in their presence and stated a belief that their employment is at risk.

        Transcript: "{{ input_prompt }}"
        Fact:
        """)

# @app.on_event("startup")
# async def startup_event():
#     global engine
#     print("Heating up the kitchen... Loading Qwen3-0.6B into CPU memory.")
#     # Force device to CPU since you mentioned running this natively without GPU
#     engine = SubtextEngine(model_id="Qwen/Qwen3-0.6B", target_layer=18, device="cpu")
#     print("Kitchen is open. Ready for React requests.")

# 3. Data Validation Models
# Pydantic ensures the React app sends exactly what we expect
class PatientRequest(BaseModel):
    transcript: str

class DiagnosticResponse(BaseModel):
    baseline: str
    insight: str
    processing_time_seconds: float

# 4. The API Endpoint
import time

@app.post("/analyze", response_model=DiagnosticResponse)
async def analyze_transcript(request: PatientRequest):
    global engine

    # load engine upon request
    engine = SubtextEngine(model_id="Qwen/Qwen3-0.6B-Base", target_layer=18, device="cpu")
    start_time = time.time()
    
    actual_text = request.transcript
    
    print(f"\n--- New Request Received ---")
    print(f"Patient: {actual_text}")
    
    # STEP 1: Generate the Baseline
    baseline_prompt = COURT_REPORTER_MATRIX.render(input_prompt=actual_text)
    
    # Assuming you added a simple generate_text method to your class for the baseline
    flat_text = engine.generate_baseline_insight(baseline_prompt)

    # STEP 2: Extract the Vector
    shadow = engine.extract_shadow_vector(actual_text, flat_text)

    # STEP 3: Steer the Insight
    clinical_prompt = """[CLINICAL OBSERVATION LOG]
    Subject: Patient Speech Pattern Analysis
    Vector Delta: Actual Utterance vs. Literal Translation
    Detected Subtext: The mathematical divergence in the patient's latent state reveals that they are currently feeling"""

    raw_insight = engine.generate_steered_insight(clinical_prompt, shadow, alpha=0.45)
    clean_insight = raw_insight.split("\n\n")[0].strip()
    print(f"Generated Insight: {clean_insight}")

    calc_time = round(time.time() - start_time, 2)
    
    # 5. Hand the meal back to the Waiter (Return JSON to React)
    return DiagnosticResponse(
        baseline=flat_text,
        insight=clean_insight,
        processing_time_seconds=calc_time
    )

if __name__ == "__main__":
    # Runs the server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8086)