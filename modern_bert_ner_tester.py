from transformers import pipeline

def test_model():
    # 1. Point the pipeline to the folder where you saved the model
    # It will automatically load the weights, tokenizer, and your custom id2label map
    model_path = "./therapy-modernbert-ner-final"
    
    print(f"Loading trained ModernBERT from {model_path}...")
    
    # Initialize the NER pipeline
    ner_pipeline = pipeline(
        "token-classification", 
        model=model_path, 
        tokenizer=model_path,
        aggregation_strategy="simple" # This glues the subwords back together
    )
    
    # 2. Feed it a brand new, unseen sentence
    test_transcript = """
    Therapist: It's good to see you again. How have things been since our last session?
    Patient: Honestly, it's been a really rough week. I haven't been able to shake this constant dread.
    Therapist: I'm sorry to hear that. Can you pinpoint when that feeling of dread usually starts?
    Patient: Usually right after I wake up. I start thinking about my upcoming performance review at work, and my chest gets incredibly tight.
    Therapist: So the performance review is acting as a trigger for that physical tightness. How are you managing that symptom when it peaks?
    Patient: Not well. I've just been avoiding my manager entirely. If I see him in the hallway, I literally turn around and walk the other way.
    Therapist: Avoidance is a very common defense mechanism, but it often reinforces the anxiety. What happens after you avoid him?
    Patient: I feel a tiny bit of relief for about five minutes, but then this overwhelming guilt sets in because I know I'm sabotaging my own career.
    Therapist: That's a classic cycle. The short-term relief is outmatched by the long-term guilt. Have you tried the box breathing technique we discussed when the chest tightness starts?
    Patient: I tried it once on Tuesday, but I couldn't focus. I just ended up taking a sick day and staying in bed.
    """

    print("\nRunning Inference...\n")
    print(f"Transcript: '{test_transcript}'\n")
    print("="*40)
    
    # 3. Run the text through the neural network
    results = ner_pipeline(test_transcript)
    
    # 4. Print the extracted entities
    if not results:
        print("The model didn't find any entities.")
    
    for entity in results:
        # The pipeline returns the exact substring, the label, and its confidence score
        word = entity['word'].strip()
        label = entity['entity_group']
        confidence = entity['score']
        
        print(f"Extracted:  {word}")
        print(f"Label:      {label}")
        print(f"Confidence: {confidence:.2%}")
        print("-" * 40)

if __name__ == "__main__":
    test_model()