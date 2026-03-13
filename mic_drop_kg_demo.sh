#!/bin/bash

API_URL="http://localhost:8086"
PAYLOAD_FILE="mic_drop_payload.json"

echo "======================================================"
echo "🎤 INITIATING GTC MIC DROP DEMO TEST"
echo "======================================================"
echo "Sanitizing and compiling massive clinical transcript..."

# Use Python to safely parse the raw text, remove training markers, and build the API schema
python3 -c '
import json
import re

raw_text = """Therapist: We haven'"'"'t talked about your family situation in a few sessions. How have things been at home since we last discussed it?

Patient: Oh god, where do I even start. So you know how my mom has this thing where she like completely rearranges my room when I'"'"'m at work? Well last week I came home and she had moved all my books to a different shelf and I couldn'"'"'t find my copy of that Python programming book I'"'"'ve been referencing for the project I'"'"'m working on and I spent literally an hour looking for it and then when I finally asked her about it she got this look on her face like I had accused her of murder and said she was just trying to help and keep things organized and I should be grateful because she'"'"'s letting me stay here rent-free and then my sister chimed in from the living room about how I'"'"'m such a perfectionist and can'"'"'t let anything go and then somehow we ended up arguing about [E2]Thanksgiving from three years ago[\/E2] and I didn'"'"'t even get my book back until this morning when I found it in the garage.

Therapist: That'"'"'s a lot of layers in that interaction. I notice you mentioned several different people - your mother, your sister - and the original conflict about the book somehow became a discussion about Thanksgiving. Can you identify what the core issue was that kept escalating?

Patient: I mean, I think the book thing shouldn'"'"'t have been a big deal in the first place, right? Like rationally I know that, and I'"'"'ve been trying to apply those breathing techniques you showed me last month, but then she gets this tone and it'"'"'s like suddenly I'"'"'m eight years old again and I'"'"'m in trouble for something I didn'"'"'t do and I just feel this wave of... I don'"'"'t know... not being allowed to have my own things or my own space or my own opinions? And then Sarah has to always make it worse by turning it into some character flaw of mine and suddenly it'"'"'s not about the book anymore, it'"'"'s about how I'"'"'m apparently difficult to live with and maybe that'"'"'s why Marcus left and maybe that'"'"'s why I can'"'"'t keep relationships together and oh god I'"'"'m doing it right now aren'"'"'t I, I'"'"'m spiraling.

Therapist: You'"'"'re not spiraling, you'"'"'re identifying a pattern. You'"'"'ve just articulated something important - the book incident triggered an emotional response that went far beyond the object itself. It connected to deeper feelings about autonomy and your place in the family. That'"'"'s the kind of core belief work we touched on in our earlier sessions.

Patient: But here'"'"'s the thing that'"'"'s really confusing me, and I'"'"'ve been thinking about this all week actually, both during my commute and during those really boring stand-up meetings where I'"'"'m supposed to be paying attention to the sprint updates but I'"'"'m just sitting there obsessing about whether I'"'"'m overreacting or not - is it even reasonable for me to want my own space? I mean, I'"'"'m thirty years old, I'"'"'m divorced, I'"'"'m living with my parents, and I can'"'"'t even have my books on the shelf where I put them. But on the other hand, they'"'"'re doing me this huge favor by letting me stay here while I figure out my finances, and my mom lost her job last month so there'"'"'s this whole thing now where I feel like I can'"'"'t even complain about anything because she needs me to be grateful and easy to live with.

Therapist: You'"'"'re describing a conflict between your need for autonomy and your sense of obligation to your family. This is common in multi-generational living situations, especially when there are financial dependencies involved. Let me ask you this - when you imagine the ideal outcome, what would that look like? Not necessarily what'"'"'s realistic, but what would feel right to you emotionally?

Patient: Oh that'"'"'s easy, I think about this all the time actually. I'"'"'d have my own apartment, even if it was tiny and in a bad neighborhood, like that one I looked at on Zillow that was literally next to the highway and had a suspicious stain on the ceiling. I'"'"'d come home to a place where no one moves my things and no one comments on what time I came in or whether I'"'"'ve eaten enough or why I'"'"'m still awake at midnight. I could have my friend Jamie over without getting that look from my mom like she'"'"'s evaluating her. I could be sad about Marcus if I wanted to be sad about Marcus, you know? Instead of performing recovery for an audience.

Therapist: What I hear is that you want a space where you can exist without being evaluated or managed. That'"'"'s not unreasonable. Now, what stops you from making that move? Is it purely financial, or are there other factors you'"'"'ve identified?

Patient: Okay so here'"'"'s where it gets really complicated and I'"'"'ve only just started to admit this to myself, let alone to anyone else. Part of me doesn'"'"'t actually want to leave. And not because I love living here with my mom reorganizing my stuff every five seconds, but because I'"'"'m terrified. Like, genuinely terrified. What if I move out and I fail? What if I can'"'"'t make the rent and I have to come back and it'"'"'s even more humiliating than leaving in the first place? And also, and this is the part I'"'"'m really ashamed of, part of me likes that my mom is still kind of taking care of me in this way. It'"'"'s horrible to admit because I'"'"'m a whole adult but sometimes when she makes me dinner and leaves it in the fridge with a little note I feel this weird comfort that I don'"'"'t get anywhere else, and then I hate myself for wanting that comfort because it comes with all this other stuff about being controlled and never being treated like an equal.

Therapist: That'"'"'s a significant self-awareness moment. You'"'"'re recognizing that you have conflicting desires - the need for independence and the comfort of being cared for. Both are valid. In integrative therapy, we would explore how these attachments formed. Can you connect this to your earlier family dynamics, perhaps your relationship with your mother before the divorce?

Patient: Oh absolutely, I mean my therapist - not you, I had a different therapist in my twenties before I moved states - she used to always say I had enmeshment issues with my mom and I used to get so angry because I thought she was saying my mom was a bad person and my mom isn'"'"'t a bad person, she'"'"'s actually a really good person who does a lot for everyone, but yeah there was definitely this thing where my emotions were her emotions and I couldn'"'"'t be sad because then she'"'"'d be sad and I had to take care of her, and I think that'"'"'s also maybe why Marcus and I didn'"'"'t work out because I'"'"'m just so used to managing other people'"'"'s feelings that I don'"'"'t even know how to just... be in my own feelings? Is that even a real thing or am I just blaming my mom for everything?

Therapist: That'"'"'s a thoughtful question. You'"'"'re not blaming your mother - you'"'"'re recognizing patterns that likely developed in childhood and understanding how they show up in your adult relationships. This isn'"'"'t about assigning blame; it'"'"'s about gaining insight. Your relationship with Marcus, your current family dynamics, and your difficulty identifying your own emotions all seem to connect to these early attachment patterns. How would you rate your ability to identify your emotions on a scale of one to ten right now?

Patient: Maybe a five? I can identify the big ones like happy, sad, angry, scared, but there'"'"'s all this stuff in between that I think I'"'"'m missing. Like this morning I was sitting in my car in the driveway for like twenty minutes before I went inside, and I knew I didn'"'"'t want to go in, but I couldn'"'"'t figure out if I was anxious or annoyed or sad or just tired, and by the time I figured it out I was late for work and I just went in anyway without understanding anything about myself. Is that normal? Do other people know what they'"'"'re feeling?

Therapist: That'"'"'s very normal, and the fact that you'"'"'re sitting with those questions is progress. Many people never develop the vocabulary for emotional granularity. We could work on that using some of the somatic experiencing techniques we discussed last month - the body scan exercises that help you identify physical sensations associated with different emotions. Have you tried those?

Patient: I tried once and I got so frustrated because I just lay there on my bed thinking am I supposed to be feeling something in my stomach or my chest and it all just felt like my body, I couldn'"'"'t distinguish between different emotions physically, and then I got distracted by my phone and then [E1]I fell asleep[\/E1]. So that was a total failure.

Therapist: It wasn'"'"'t a failure - it was practice. The inability to distinguish physical sensations is actually common and improves with repetition. Let'"'"'s try a different approach in our next session. For now, let'"'"'s return to the family conflict. You mentioned your sister Sarah added to the tension. What'"'"'s your relationship with her typically like?

Patient: Sarah is... she'"'"'s two years younger than me and she'"'"'s always kind of been the favorite, I think, or at least that'"'"'s how it felt growing up. She'"'"'s married, she has two kids, she lives in the nice suburban house with the white picket fence, and my parents just adore her husband David, they talk about him constantly like he'"'"'s the son they never had. And I know that'"'"'s not fair to Sarah because she'"'"'s probably also struggling with her own things, she'"'"'s definitely not as put-together as she looks on Instagram, but whenever I'"'"'m around her I just feel like this unfinished version of a person, like I'"'"'m the rough draft and she'"'"'s the final publication.

Therapist: I notice you'"'"'ve used some strong comparisons - rough draft versus final publication. That suggests there might be some internalized judgment about your life path, particularly post-divorce. How much of this feeling comes from your own perception versus feedback you'"'"'ve actually received from your family?

Patient: That'"'"'s a really good question and I'"'"'ve thought about it and I think... I think most of it is in my head? Like my mom has never explicitly said I'"'"'m a disappointment or anything, she actually says the opposite a lot, she'"'"'s always saying how strong I am and how brave I was to leave Marcus, but then she'"'"'ll also ask me every single week if I'"'"'ve tried couples therapy with him like maybe I didn'"'"'t try hard enough, and that'"'"'s not the same as saying I'"'"'m a failure but it kind of feels like it? And my dad never says anything, which is somehow worse, because I can'"'"'t even argue with his silence, I just have to sit there wondering what he'"'"'s thinking.

Therapist: So what I'"'"'m hearing is that the messages you'"'"'re receiving are mixed, which creates cognitive ambiguity. Your mother gives verbal reassurance but also implicitly questions your decision. Your father remains silent. This inconsistency might be more destabilizing than outright criticism. How does that uncertainty affect your day-to-day functioning?

Patient: It makes me completely paranoid, honestly. I over-analyze everything. Like last week my mom asked if I wanted to go to this work event with her, this networking thing for people in tech, and I said sure that sounds fun, and then she got this weird look and said actually maybe you should stay home and rest, you look tired, and I spent the entire next hour wondering if she actually thought I looked tired or if she just didn'"'"'t want me to come because I'"'"'d embarrass her or if she was testing me to see if I'"'"'d push back or what. I don'"'"'t even know what I think anymore, I just have all this noise in my head all the time about what everyone means by everything.

Therapist: That'"'"'s a significant amount of mental energy being spent on interpretation and prediction. This hypervigilance around family communication is consistent with what we'"'"'ve discussed about your attachment style. For our work going forward, I'"'"'d like to explore two parallel tracks - continuing to build your emotional granularity skills, and also examining whether there'"'"'s a way to create healthier boundaries with your family without completely severing the relationship. How does that sound to you?"""

# Sanitize RE tokens
clean_text = re.sub(r"\[/?E[12]\]|\[\\/E[12]\]", "", raw_text)

# Parse into Diarization Schema
transcript = []
blocks = clean_text.split("\n\n")
for block in blocks:
    if ":" in block:
        speaker, text = block.split(":", 1)
        transcript.append({
            "speaker": speaker.strip(),
            "text": text.strip()
        })

payload = {
  "patient_id": "gtc-demo-enmeshment-002",
  "transcript_payload": {
    "transcript": transcript
  },
  "inference_config": {
    "max_context_tokens": 8192,
    "window_overlap_tokens": 1000,
    "relation_batch_size": 8
  }
}

with open("'$PAYLOAD_FILE'", "w") as f:
    json.dump(payload, f)
'

echo "Payload built. Submitting to local ModernBERT pipeline..."

RESPONSE=$(curl -s -X POST "$API_URL/api/knowledge-graph" \
  -H "Content-Type: application/json" \
  -d @$PAYLOAD_FILE)

JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id // empty')

if [ -z "$JOB_ID" ]; then
    echo "❌ Failed to queue the job. API responded with:"
    echo "$RESPONSE" | jq .
    rm $PAYLOAD_FILE
    exit 1
fi

echo "✅ Job queued! Job ID: $JOB_ID"
echo -n "Crunching matrices on local metal"

STATUS="processing"
while [ "$STATUS" == "processing" ]; do
    sleep 2
    echo -n "."
    POLL_RESPONSE=$(curl -s -X GET "$API_URL/api/jobs/$JOB_ID")
    STATUS=$(echo "$POLL_RESPONSE" | jq -r '.status // "failed"')
done

echo ""
echo "======================================================"

if [ "$STATUS" == "completed" ]; then
    echo "🎉 MIC DROP COMPLETE!"
    echo "Graph Stats:"
    echo "$POLL_RESPONSE" | jq '.result.stats'
    echo ""
    echo "Check LadybugDB UI at http://localhost:8000 for patient: gtc-demo-enmeshment-001"
else
    echo "🔥 Job Failed!"
    echo "Error Details:"
    echo "$POLL_RESPONSE" | jq .
fi

rm $PAYLOAD_FILE