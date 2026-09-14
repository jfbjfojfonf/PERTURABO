#!/usr/bin/env python3
"""
B-roll Scorer — Score les segments pour le placement de B-roll.
"""

import json


# Duration rules
DURATION_RULES = {
    15: 1,
    30: 3,
    45: 3,
    60: 4,
    90: 5,
    120: 6
}

# Minimum gap between B-roll (seconds)
MIN_GAP = 5

# Never place B-roll on these
NEVER_PLACE = ["hook", "emotion_peak", "punchline", "silence"]

# Always place B-roll on these
ALWAYS_PLACE = ["enumeration", "visual_trigger", "context_gap", "dead_air"]


def get_max_broll(duration_sec):
    """Get max B-roll count based on clip duration."""
    for d in sorted(DURATION_RULES.keys()):
        if duration_sec <= d:
            return DURATION_RULES[d]
    return DURATION_RULES[120]


def score_broll_moment(text, start_sec):
    """Score a moment for B-roll placement."""
    text_lower = text.lower()
    score = 0
    reasons = []

    # Visual trigger (+3)
    visual_words = ["look", "see", "imagine", "picture", "this guy", "she said"]
    for w in visual_words:
        if w in text_lower:
            score += 3
            reasons.append(f"visual_trigger: '{w}'")
            break

    # Context gap (+3)
    context_words = ["look at what happened", "the result", "when that happened", "you won't believe"]
    for w in context_words:
        if w in text_lower:
            score += 3
            reasons.append(f"context_gap: '{w}'")
            break

    # Enumeration (+2)
    enum_words = ["first", "second", "third", "number one", "number two"]
    for w in enum_words:
        if w in text_lower:
            score += 2
            reasons.append(f"enumeration: '{w}'")
            break

    # Description words (+2)
    desc_words = ["imagine", "picture this", "you see", "she said", "he told me"]
    for w in desc_words:
        if w in text_lower:
            score += 2
            reasons.append(f"description: '{w}'")
            break

    # Dead air (+2)
    if any(p in text_lower for p in ["...", "um", "uh", "so..."]):
        score += 2
        reasons.append("dead_air")

    # Emotion peak (+1 but NO B-roll)
    if any(w in text_lower for w in ["!", "insane", "destroyed", "crazy"]):
        score += 1
        reasons.append("emotion_peak → SKIP")

    return score, reasons


def select_broll_moments(segments, duration_sec):
    """Select the best moments for B-roll placement."""
    max_broll = get_max_broll(duration_sec)

    # Score all segments
    scored = []
    for seg in segments:
        score, reasons = score_broll_moment(seg.get("text", ""), seg.get("start", 0))
        scored.append({
            "segment": seg,
            "score": score,
            "reasons": reasons
        })

    # Sort by score
    scored.sort(key=lambda x: x["score"], reverse=True)

    # Select top N, respecting minimum gap
    selected = []
    last_end = -MIN_GAP

    for s in scored:
        if len(selected) >= max_broll:
            break

        seg_start = s["segment"].get("start", 0)
        if seg_start - last_end < MIN_GAP:
            continue

        # Skip emotion peaks
        if "emotion_peak → SKIP" in s["reasons"]:
            continue

        selected.append({
            "id": f"broll_{len(selected)+1}",
            "start_sec": seg_start,
            "score": s["score"],
            "reasons": s["reasons"],
            "text": s["segment"].get("text", "")
        })
        last_end = seg_start + s["segment"].get("duration", 3)

    return selected, max_broll
