#!/usr/bin/env python3
"""
Transcript Analyzer — Analyse les transcripts pour trouver les moments viraux.
"""

import json
import re


# Mots-clés par catégorie
VISUAL_TRIGGERS = [
    "look", "see", "imagine", "picture", "this guy", "she said",
    "he told", "watch", "check out", "right here", "this moment"
]

EMOTION_WORDS = [
    "shocking", "insane", "crazy", "unbelievable", "wow", "omg",
    "hilarious", "epic", "destroyed", "destroying", "obliterated"
]

CONTROVERSY_WORDS = [
    "controversy", "scandal", "lie", "cheat", "fight", "drama",
    "exposed", "caught", "fired", "arrested", "banned"
]

ENUMERATION_WORDS = [
    "first", "second", "third", "number one", "number two",
    "step one", "step two", "finally", "lastly"
]

DESCRIPTION_WORDS = [
    "imagine", "picture this", "you see", "you know", "basically",
    "essentially", "literally", "actually"
]

DEAD_AIR_PATTERNS = [
    r"\.\.\.",  # Ellipsis
    r"um+",     # Hesitation
    r"uh+",     # Hesitation
    r"so\s+...", # Trailing off
]


def score_segment(text):
    """Score a text segment for viral potential."""
    text_lower = text.lower()
    score = 0
    reasons = []

    # Visual triggers (+3)
    for w in VISUAL_TRIGGERS:
        if w in text_lower:
            score += 3
            reasons.append(f"visual_trigger: '{w}'")
            break

    # Emotion words (+2)
    for w in EMOTION_WORDS:
        if w in text_lower:
            score += 2
            reasons.append(f"emotion: '{w}'")
            break

    # Controversy (+2)
    for w in CONTROVERSY_WORDS:
        if w in text_lower:
            score += 2
            reasons.append(f"controversy: '{w}'")
            break

    # Enumeration (+2)
    for w in ENUMERATION_WORDS:
        if w in text_lower:
            score += 2
            reasons.append(f"enumeration: '{w}'")
            break

    # Description words (+2)
    for w in DESCRIPTION_WORDS:
        if w in text_lower:
            score += 2
            reasons.append(f"description: '{w}'")
            break

    # Dead air (+2)
    for pattern in DEAD_AIR_PATTERNS:
        if re.search(pattern, text_lower):
            score += 2
            reasons.append("dead_air")
            break

    # Emotion peak detection (+1 but NO B-roll)
    if any(w in text_lower for w in ["!", "insane", "destroyed", "obliterated"]):
        score += 1
        reasons.append("emotion_peak")

    return score, reasons


def analyze_transcript(transcript, n_moments=5):
    """Analyze a transcript and return top N viral moments."""
    segments = transcript.get("segments", [])
    scored = []

    for i, seg in enumerate(segments):
        text = seg.get("text", "")
        score, reasons = score_segment(text)

        if score > 0:
            scored.append({
                "segment_id": f"S{i+1:03d}",
                "index": i,
                "start": seg.get("start", 0),
                "duration": seg.get("duration", 0),
                "text": text,
                "score": score,
                "reasons": reasons
            })

    # Sort by score
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Take top N
    top = scored[:n_moments]

    # Add moment IDs
    for i, m in enumerate(top):
        m["moment_id"] = f"M{i+1:02d}"

    return top
