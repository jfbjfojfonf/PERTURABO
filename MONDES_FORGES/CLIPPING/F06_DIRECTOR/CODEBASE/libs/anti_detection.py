#!/usr/bin/env python3
"""
Anti-Detection — Génère les instructions anti-détection pour chaque clip.
"""

import json


# Style-specific anti-detection presets
STYLE_PRESETS = {
    "ranking": {
        "mirror": True,
        "zoom": {"type": "punch", "start_pct": 100, "end_pct": 115},
        "speed": {"base": 1.0, "variations": [{"at_sec": 15, "speed": 1.05, "duration_sec": 3}]},
        "sfx_count": "5-6",
        "crop": {"top_pct": 0.02, "bottom_pct": 0.02, "left_pct": 0.01, "right_pct": 0.01}
    },
    "reframing": {
        "mirror": False,
        "zoom": {"type": "slow_push_in", "start_pct": 100, "end_pct": 108},
        "speed": {"base": 1.0, "variations": [{"at_sec": 15, "speed": 1.05, "duration_sec": 3}]},
        "sfx_count": "1-2",
        "crop": {"top_pct": 0.02, "bottom_pct": 0.02, "left_pct": 0.01, "right_pct": 0.01}
    },
    "blur": {
        "mirror": False,
        "zoom": {"type": "breathing", "start_pct": 100, "end_pct": 110},
        "speed": {"base": 1.0, "variations": [{"at_sec": 15, "speed": 1.05, "duration_sec": 3}]},
        "sfx_count": "1-2",
        "crop": None
    }
}

# Default SFX
DEFAULT_SFX = [
    {"type": "whoosh", "at_sec": 3.0, "volume_db": -18, "reason": "transition after hook"},
    {"type": "boom", "at_sec": 15.0, "volume_db": -15, "reason": "punchline emphasis"}
]


def generate_anti_detection(style, clip_duration_sec=30):
    """Generate anti-detection instructions for a clip."""
    preset = STYLE_PRESETS.get(style, STYLE_PRESETS["ranking"])

    anti_detection = {
        "mirror": preset["mirror"],
        "zoom": preset["zoom"],
        "speed": preset["speed"],
        "sfx": DEFAULT_SFX[:2] if style != "ranking" else DEFAULT_SFX,
        "crop": preset["crop"]
    }

    return anti_detection


def validate_anti_detection(anti_detection):
    """Validate that anti-detection meets minimum requirements."""
    issues = []

    # Must have at least 1 visual treatment
    has_visual = (
        anti_detection.get("mirror") or
        anti_detection.get("zoom") or
        anti_detection.get("crop")
    )
    if not has_visual:
        issues.append("Missing visual treatment (mirror/zoom/crop)")

    # Must have at least 1 audio treatment
    has_audio = anti_detection.get("sfx")
    if not has_audio:
        issues.append("Missing audio treatment (SFX)")

    return len(issues) == 0, issues
