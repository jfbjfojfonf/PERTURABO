#!/usr/bin/env python3
"""
pur_adapter.py - Adaptateur Mode PUR (skip F01_SCOUT)
=====================================================
Transforme la sortie de F00B_VOX (candidats.json) en `source_specimen.json`
compatible F02_TYRANT_CAMP, en court-circuitant F01_SCOUT (redondant en PUR).

Doctrine PUR :
  - strict-source : les assets = les candidats VOX (segments de la VOD).
  - reference_clip = None (optionnel en PUR, cf. GUIDE 13).
  - Aucune re-transcription : VOX a deja tout transcrit/scoré.

Usage :
  python pur_adapter.py --candidats <candidats.json> --directive <directive.md> \
         --vod <url> --out <source_specimen.json>
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "SHARED"))
from candidates_reader import CandidatesReadError, load_candidates_document  # noqa: E402


def _load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _campaign_id(md_text):
    m = re.search(r"Campaign ID:\s*(.+)", md_text)
    if m:
        return m.group(1).strip().strip("*").strip()
    return "pur_unknown"


def main():
    ap = argparse.ArgumentParser(description="Adaptateur PUR : VOX -> source_specimen F02")
    ap.add_argument("--candidats", required=True)
    ap.add_argument("--directive", required=True)
    ap.add_argument("--vod", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    try:
        cands = load_candidates_document(args.candidats)
    except CandidatesReadError as exc:
        print("[PUR_ADAPTER] ERREUR: {}".format(exc), file=sys.stderr)
        sys.exit(1)
    candidates = cands.get("candidates", [])

    directive_md = open(args.directive, "r", encoding="utf-8").read()
    campaign_id = _campaign_id(directive_md)

    assets = []
    for c in candidates:
        assets.append({
            "asset_id": c.get("candidate_id") or "vox_{}".format(c.get("start_sec")),
            "type": "stream_segment",
            "url": args.vod,
            "start_sec": c.get("start_sec"),
            "end_sec": c.get("end_sec"),
            "duration_sec": c.get("duration_sec"),
            "signal_type": c.get("signal_type"),
            "signal_intensity": c.get("signal_intensity"),
            "transcript_available": True,
            "vox_source": "F00B_VOX",
        })

    specimen = {
        "campaign_id": campaign_id,
        "scanned_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "pur",
        "reference_clip": None,
        "assets": assets,
        "vox_notes": "Mode PUR : F01_SCOUT skip (redondant avec F00B_VOX). Assets = candidats VOX.",
        "check_in_iw_custos": None,
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(specimen, f, indent=2, ensure_ascii=False)
    print("[PUR_ADAPTER] source_specimen.json -> {} ({} assets)".format(args.out, len(assets)))


if __name__ == "__main__":
    main()
