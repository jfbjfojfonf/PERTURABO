#!/usr/bin/env python3
"""
Montage Builder — Assemble les instructions de montage complètes.
"""

import json


# Pacing presets by style
PACING = {
    "ranking": "fast",
    "reframing": "medium",
    "blur": "medium"
}

# Energy curves by style
ENERGY_CURVES = {
    "ranking": ["hook_100", "build_70", "punchline_100", "outro_50"],
    "reframing": ["hook_100", "context_60", "build_80", "conclusion_50"],
    "blur": ["hook_100", "context_60", "build_80", "conclusion_50"]
}

# Zoom patterns by style
ZOOM_PATTERNS = {
    "ranking": [
        {"start_sec": 0, "end_sec": 3, "zoom_pct": 100},
        {"start_sec": 3, "end_sec": 15, "zoom_pct": 110},
        {"start_sec": 15, "end_sec": 25, "zoom_pct": 115},
        {"start_sec": 25, "end_sec": 30, "zoom_pct": 100}
    ],
    "reframing": [
        {"start_sec": 0, "end_sec": 3, "zoom_pct": 100},
        {"start_sec": 3, "end_sec": 30, "zoom_pct": 108}
    ],
    "blur": [
        {"start_sec": 0, "end_sec": 3, "zoom_pct": 100},
        {"start_sec": 3, "end_sec": 15, "zoom_pct": 105},
        {"start_sec": 15, "end_sec": 30, "zoom_pct": 110}
    ]
}


def build_montage_instructions(style, clip_duration_sec=30, broll_schedule=None):
    """Build complete montage instructions."""
    instructions = {
        "hook_duration_sec": 3,
        "total_duration_sec": clip_duration_sec,
        "pacing": PACING.get(style, "medium"),
        "energy_curve": ENERGY_CURVES.get(style, ENERGY_CURVES["ranking"]),
        "zoom_pattern": ZOOM_PATTERNS.get(style, ZOOM_PATTERNS["ranking"]),
        "broll_inserts": []
    }

    # Add B-roll inserts
    if broll_schedule:
        for broll in broll_schedule:
            instructions["broll_inserts"].append({
                "id": broll.get("id", "broll_?"),
                "insert_at_sec": broll.get("start_sec", 0),
                "duration_sec": 2,
                "source": broll.get("source", "campaign"),
                "cut_in": broll.get("cut_in", "0:00"),
                "cut_out": broll.get("cut_out", "0:02")
            })

    return instructions


def build_production_pack(segment, text_payload, style, broll_schedule, anti_detection):
    """Build the complete production pack for OMNIS_WATCH."""
    pack = {
        "clip_id": f"pur_{segment.get('moment_id', 'unknown').lower()}",
        "style": style,
        "segment": {
            "moment_id": segment.get("moment_id"),
            "start_sec": segment.get("start", 0),
            "duration_sec": segment.get("duration", 30),
            "text": segment.get("text", "")
        },
        "text_payload": {
            "title": text_payload.get("title", ""),
            "hook_text": text_payload.get("hook_text", ""),
            "captions": text_payload.get("captions", []),
            "metadata": text_payload.get("metadata", {})
        },
        "broll_schedule": broll_schedule,
        "anti_detection": anti_detection,
        "montage_instructions": build_montage_instructions(
            style,
            segment.get("duration", 30),
            broll_schedule
        )
    }

    return pack
