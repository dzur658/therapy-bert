import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

class SubtextEngine:
    def __init__(self, model_id="Qwen/Qwen3-0.6B-Base", target_layer=-10, device="cuda" if torch.cuda.is_available() else "cpu"):
        """
        Initializes the Representation Engineering pipeline for on-device inference.
        Loads the Base model strictly for Document Continuation, avoiding alignment taxes.
        """
        print(f"Loading {model_id} onto {device}...")
        self.device = device
        self.target_layer = target_layer
        
        # Load the base model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id, 
            dtype=torch.bfloat16, 
            device_map=self.device
        )
        
        # Resolve the actual layer index (e.g., -6 translates to layer 18 in a 24-layer model)
        self.num_layers = len(self.model.model.layers)
        self.actual_target_layer = self.num_layers + self.target_layer if self.target_layer < 0 else self.target_layer
        print(f"Engine initialized. Surgical hooks will target Layer {self.actual_target_layer} / {self.num_layers - 1}")

    def _get_layer_hidden_state(self, text: str) -> torch.Tensor:
        """
        Passes text through the model and passively wires a hook to grab the target layer's output.
        Returns the mathematically isolated 1D vector of the final token.
        """
        inputs = self.tokenizer(text, return_tensors="pt").to(self.device)
        captured_tensor = None

        def extraction_hook(module, input, output):
            nonlocal captured_tensor
            # 1. Dynamic tuple check (handles Hugging Face architectural shifts)
            hs = output[0] if isinstance(output, tuple) else output
            
            # 2. Extract the last token's 1D vector safely
            if hs.dim() == 3:
                captured_tensor = hs[0, -1, :].detach().clone()
            elif hs.dim() == 2:
                captured_tensor = hs[-1, :].detach().clone()
            else:
                raise ValueError(f"Unexpected hidden states dimension: {hs.shape}")

        # Attach the wiretap
        layer_module = self.model.model.layers[self.actual_target_layer]
        handle = layer_module.register_forward_hook(extraction_hook)
        
        with torch.no_grad():
            self.model(**inputs)
            
        handle.remove()
        return captured_tensor

    def extract_shadow_vector(self, actual_transcript: str, literal_translation: str) -> torch.Tensor:
        """
        Calculates the high-dimensional delta between the patient's actual words and the literal topic.
        """
        h_actual = self._get_layer_hidden_state(actual_transcript)
        h_literal = self._get_layer_hidden_state(literal_translation)
        
        # The Math: Subtracting the literal topic leaves only the emotional/pragmatic subtext
        shadow_vector = h_actual - h_literal
        return shadow_vector

    def generate_steered_insight(self, prompt: str, shadow_vector: torch.Tensor, alpha: float = 2.0, max_tokens: int = 50) -> str:
        """
        Generates text using Document Continuation while actively injecting the L2-normalized 
        shadow vector back into the residual stream to steer the model's psychological analysis.
        """
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        shadow_vector = shadow_vector.to(self.device)

        def injection_hook(module, input, output):
            is_tuple = isinstance(output, tuple)
            current_hs = output[0].clone() if is_tuple else output.clone()
            
            is_3d = current_hs.dim() == 3

            # Align for broadcasting [1, 1, hidden_dim]
            shadow_aligned = shadow_vector.unsqueeze(0).unsqueeze(0) if is_3d else shadow_vector.unsqueeze(0)
                
            # THE FIX: Add the shadow to ALL tokens in the sequence simultaneously
            current_hs = current_hs + alpha * shadow_aligned

            return (current_hs,) + output[1:] if is_tuple else current_hs

        # Attach the IV drip
        layer_module = self.model.model.layers[self.actual_target_layer]
        handle = layer_module.register_forward_hook(injection_hook)
        
        # Generate the insight
        with torch.no_grad():
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                # temperature=0.0, # Keep low; the math is doing the heavy lifting, not the RNG
                do_sample=False,
                repetition_penalty=1.2, # Mild penalty to encourage novel insights
                pad_token_id=self.tokenizer.eos_token_id,
            )
            
        handle.remove()
        
        # Decode only the newly generated tokens (ignoring the prompt)
        input_length = inputs.input_ids.shape[1]
        response = self.tokenizer.decode(generated_ids[0][input_length:], skip_special_tokens=True)
        return response.split("\n")[0].strip()  # Return only the first line for clarity

    def generate_baseline_insight(self, input_prompt: str, max_tokens: int = 50) -> str:
        """
        Generates insight without any steering for a baseline comparison.
        """

        # full_prompt = f"""
        # Convert the subjective transcript into a sterile, physical, and objective Court Reporter fact.

        # Transcript: "He is a complete idiot for doing that behind my back! I hate him!"
        # Fact: The subject stated that a secondary individual took an action without their prior knowledge.

        # Transcript: "Oh, you know, just another day in paradise! My car broke down, but hey, I didn't get hit by a bus!"
        # Fact: The subject experienced a mechanical vehicle failure and remained physically uninjured.

        # Transcript: "I don't know... It doesn't really matter what I do, does it? I'll just sit here and see what happens."
        # Fact: The subject indicated a lack of preference for future actions and stated they will wait.

        # Transcript: "I haven't slept in three days because I'm finally figuring out the algorithm, it's all connected, I just need more coffee!"
        # Fact: The subject reported being awake for 72 hours working on a mathematical problem and expressed a need for caffeine.

        # Transcript: "Sure, whatever. I guess I'll just keep doing exactly what she says. It's fine. I'm used to it."
        # Fact: The subject agreed to comply with the instructions provided by a female individual.

        # Transcript: "I can't go back in there. My chest is tight, I can't breathe, everyone is just staring at me waiting for me to fail."
        # Fact: The subject expressed an unwillingness to re-enter the room, reported respiratory physical sensations, and stated others were observing them.

        # Transcript: "It feels like a hole in my chest. I keep waiting for him to walk through the door, but he never does. It's so quiet."
        # Fact: The subject described a physical sensation in their chest and noted the continued absence of a male individual in their environment.

        # Transcript: "No, I'm not mad he forgot our anniversary. His startup is in a critical phase. Work is important. It's a logical prioritization."
        # Fact: The subject stated their partner missed an anniversary due to professional commitments and acknowledged the logistical reasoning.

        # Transcript: "I'm such a monster. I shouldn't have yelled at the kids like that, I ruined the whole weekend."
        # Fact: The subject recalled raising their voice at children and stated this action negatively impacted the weekend schedule.

        # Transcript: "There's just too much! The emails, the deadlines, the house is a mess, I'm drowning in all of this!"
        # Fact: The subject listed multiple uncompleted tasks, including digital correspondence, professional deadlines, and household maintenance.

        # Transcript: "They keep whispering when I walk by. I know they're trying to get me fired, I can see it in their eyes."
        # Fact: The subject reported observing colleagues speaking quietly in their presence and stated a belief that their employment is at risk.

        # Transcript: "{input_prompt}"
        # Fact:
        # """

        full_prompt = input_prompt

        inputs = self.tokenizer(full_prompt, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            generated_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=False,
                repetition_penalty=1.2,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        
        input_length = inputs.input_ids.shape[1]
        response = self.tokenizer.decode(generated_ids[0][input_length:], skip_special_tokens=True)
        return response.split("\n")[0].strip()  # Return only the first line for clarity

# ==========================================
# GTC DEMO EXECUTION
# ==========================================
if __name__ == "__main__":
    # Initialize the engine
    engine = SubtextEngine()

    # 1. The Raw Data
    actual_text = "No, I'm not mad he forgot our anniversary. He's busy. His startup is in a critical phase. Work is important. It's a completely logical prioritization. I completely understand the math."
    print("Actual Patient Utterance:")
    print(actual_text)

    # flat_text = "Patient: My partner forgot our anniversary due to work commitments. I recognize the logistical reasons for this."

    flat_text = engine.generate_baseline_insight(actual_text)
    print("Baseline Statement as:")
    print(flat_text)

    # 2. Extract the Shadow
    print("\nIsolating latent shadow vector...")
    shadow = engine.extract_shadow_vector(actual_text, flat_text)

    # 3. Base Model Document Continuation Prompt
    prompt = """[CLINICAL OBSERVATION LOG]
    Subject: Patient Speech Pattern Analysis
    Vector Delta: Actual Utterance vs. Literal Translation
    Detected Subtext: The mathematical divergence in the patient's latent state reveals that they are currently feeling"""

    # 4. Steer and Generate
    print(f"Injecting shadow vector (alpha=0.45) into Layer {engine.actual_target_layer}...\n")
    insight = engine.generate_steered_insight(prompt, shadow, alpha=0.45)
    
    print("The patient is feeling:")
    print(insight.split("\n")[0])