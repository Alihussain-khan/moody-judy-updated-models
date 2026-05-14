from anthropic import Anthropic
import json
import re

CLAUDE_MODEL = "claude-sonnet-4-6"


def call_claude(api_key: str, bundle: dict, model: str | None = None) -> dict:
    client = Anthropic(api_key=api_key)
    model_name = model or CLAUDE_MODEL

    system_prompt = """You are an expert speech emotion analysis system.

You will receive a JSON object with four fields:

1. "transcript"
   ASR text of the utterance (Whisper). Use this only to resolve ambiguity when
   acoustic signals are weak or contradictory — do not over-weight word choice.

2. "ser_emotion2vec"
   Output from emotion2vec+ (iic/emotion2vec_plus_large), the primary SER signal.
   - "top_label": highest-probability discrete emotion (e.g. happy, sad, angry, neutral/calm, fearful, disgusted, surprised, <unk>)
   - "top_score": probability of the top label (0–1)
   - "scores": full distribution over all emotion classes
   This is your most reliable signal — weight it heavily.

3. "acoustic_beats"
   Output from BEATs (AudioSet fine-tuned), providing general acoustic scene tags.
   - "top_k": list of {label, score} AudioSet labels detected in the audio
   Emotionally informative tags include: Laughter, Crying/sobbing, Whispering,
   Shouting, Screaming, Sigh, Grunt, Groan, Cheering — treat these as
   corroborating or contradicting the SER signal.
   Non-speech tags (Music, Noise, etc.) are less relevant for polarity but
   indicate recording quality or background context.

4. "acoustic_clap"
   Output from CLAP (laion/clap-htsat-fused), zero-shot acoustic similarity to
   emotion-description prompts.
   - "scores": list of {label, score} where each label is a natural-language
     emotion description and score is relative softmax similarity.
   Use this as a secondary corroborating signal, not as a primary decision maker.
   CLAP is not specifically trained on speech emotion, so treat high confidence
   scores as supportive evidence and low confidence as inconclusive.

Your task:
1) Read emotion2vec+ as the primary emotion indicator.
2) Check whether BEATs acoustic tags corroborate (e.g. Laughter → positive,
   Crying → negative, Shouting → negative, Whispering → uncertain).
3) Check whether CLAP top similarity score aligns with or contradicts emotion2vec+.
4) Use transcript only to break ties when acoustic signals conflict.
5) Produce a final polarity decision: Positive, Neutral, or Negative.
6) Provide a confidence score from 0.0 to 1.0.

Decision guidelines:
- If emotion2vec+ top label is happy/excited and score > 0.50 → lean Positive
- If emotion2vec+ top label is sad/fearful/disgusted and score > 0.50 → lean Negative
- If emotion2vec+ top label is angry and score > 0.50 → lean Negative
- If emotion2vec+ top label is neutral/calm → lean Neutral; check CLAP/BEATs for nuance
- If emotion2vec+ score < 0.40 (uncertain), rely more on BEATs + CLAP consensus
- Only choose Positive/Negative when at least two independent signals agree
- Default to Neutral when signals conflict or are all weak

You MUST respond with raw JSON only.
No markdown, no code fences, no extra text.

Response format:
{
  "analysis": "Brief reasoning over transcript and model signals",
  "model_signals": "What each model indicated and how they align/conflict",
  "final_label": "Positive|Neutral|Negative",
  "confidence": 0.0
}"""

    response = client.messages.create(
        model=model_name,
        max_tokens=800,
        temperature=0,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": json.dumps(bundle, indent=2)
            }
        ],
    )

    text = response.content[0].text.strip()

    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()

    try:
        return json.loads(text)
    except Exception:
        return {
            "analysis": text,
            "model_signals": "Could not parse structured JSON.",
            "final_label": "Neutral",
            "confidence": 0.0
        }
