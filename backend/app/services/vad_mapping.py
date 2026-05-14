from __future__ import annotations

from typing import Dict, Literal

Polarity = Literal["Negative", "Neutral", "Positive"]

def vad_to_polarity(vad: Dict[str, float]) -> Polarity:
    v = float(vad["valence"])
    a = float(vad["arousal"])
    d = float(vad["dominance"])

    V_POS, V_NEG = 0.55, 0.45
    A_HI, A_LO = 0.55, 0.45
    D_HI, D_LO = 0.55, 0.45

    if v >= V_POS:
        return "Positive"
    if v <= V_NEG:
        return "Negative"

    # valence ambiguous → use arousal+dominance
    if a <= A_LO and d <= D_LO:
        return "Negative"
    if a >= A_HI and d >= D_HI:
        return "Positive"
    return "Neutral"