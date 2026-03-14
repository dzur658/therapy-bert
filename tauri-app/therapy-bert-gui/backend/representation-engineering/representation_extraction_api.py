import gc

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

        Transcript: "I don't even know where to start with the audit next week. The accounting team hasn't sent me the Q3 files, and my manager keeps asking for updates every two hours. I tried to log into the portal yesterday and my access was revoked, which makes me think they are setting me up to take the fall. If I complain to HR, they'll just protect the company, so I'm basically just sitting here waiting to be fired while pretending to type."
        Fact: The subject reported missing required files for an upcoming audit, noted frequent status requests from their manager, detailed a loss of system access, and stated a belief that they will be terminated without recourse from human resources.

        Transcript: "I just do not understand why my fiancée is so frustrated with me; I am doing everything right. We bought the house, we have the registry, I am checking all the boxes. It is just... I look at my buddy David, who just blew up his whole life to move to the city and finally be true to himself, and I think about how incredibly selfish that is. I would never do that, because stability is what matters, and you just have to push through the numbness to build the life you are supposed to build, right?"
        Fact: The subject reported completing standard pre-marital tasks including purchasing a home, expressed confusion regarding their partner's frustration, criticized a male friend's relocation, and stated a commitment to prioritizing stability despite experiencing emotional numbness.

        Transcript: "I love my girlfriend, obviously. We have been together for four years. But lately, I just feel this weird exhaustion when we are together. Like I have to consciously remember to hold her hand, or remember to say the right romantic things. And then my coworker, Mark, came out as gay last week, and everyone at the office was clapping for him. I just sat there feeling this intense, suffocating anger. I do not even know why. He is embarrassing himself. You do not just get to change the rules because you feel like it. You pick a path, you make it work, and you lock it down. That is what being a man is."
        Fact: The subject noted a four-year relationship with a female partner requiring conscious effort to maintain affection, reported experiencing anger when a male colleague disclosed his sexual orientation at work, and expressed a belief that men should adhere strictly to their initial life choices.

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
    reveal: str

class DiagnosticResponse(BaseModel):
    baseline: str
    insight: str
    processing_time_seconds: float

# 4. The API Endpoint
import time

@app.post("/analyze", response_model=DiagnosticResponse)
async def analyze_transcript(request: PatientRequest):
    global engine

    # find proper device to load on
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    # load engine upon request
    engine = SubtextEngine(model_id="Qwen/Qwen3-0.6B-Base", target_layer=18, device=device)
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

    insight_to_gain = request.reveal.lower()

    # STEP 3: Steer the Insight
    clinical_prompt = f"""[CLINICAL OBSERVATION LOG]
    Subject: Patient Speech Pattern Analysis
    Vector Delta: Actual Utterance vs. Literal Translation
    Detected Subtext: The mathematical divergence in the patient's latent state reveals that they are currently {insight_to_gain}"""

    raw_insight = engine.generate_steered_insight(clinical_prompt, shadow, alpha=0.45)

    clean_insight = raw_insight.split("\n\n")[0].strip()

    calc_time = round(time.time() - start_time, 2)

    # clean up memory after processing
    del engine
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    elif torch.backends.mps.is_available():
        torch.mps.empty_cache()
    
    # 5. Hand the meal back to the Waiter (Return JSON to React)
    return DiagnosticResponse(
        baseline=flat_text,
        insight=clean_insight,
        processing_time_seconds=calc_time
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8087)