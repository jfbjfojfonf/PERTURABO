#!/usr/bin/env python3
"""Seed démo SALLE DE GUERRE — Sophie Rain (démo reproductible, hors réseau).

Remplit docs/data/war_room.json avec un payload conforme au contrat F00C
(PLAN_SALLE_DE_GUERRE.md §4) pour visualiser le dashboard sans attendre le
run GitHub Actions réel. Ré-exécutable sans créer de doublon (run_id fixe).

Usage : python3 war_room/seed_demo.py
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "docs" / "data" / "war_room.json"
RUN_ID = "f00c_demo_sophie_rain"

DURATION = 600.0  # vidéo de démonstration : 10 minutes


def _bucket(i: int, n: int) -> dict:
    span = DURATION / n
    start, end = i * span, (i + 1) * span
    # courbe d'attention synthétique : pics à ~25% (ouverture choc), ~55%, ~82%
    base = 0.25 + 0.1 * ((i * 37) % 7) / 7
    for peak, amp in ((0.25, 0.55), (0.55, 0.75), (0.82, 0.9)):
        d = abs(i / n - peak)
        if d < 0.06:
            base += amp * (1 - d / 0.06) ** 2
    attention = round(min(base, 1.0), 4)
    return {"bucket": i, "start_sec": round(start, 2), "end_sec": round(end, 2),
            "attention": round(attention * 0.8, 4), "attention_norm": attention}


def _replayed(i: int, n: int) -> dict:
    span = DURATION / 25
    start, end = i * span, (i + 1) * span
    base = 0.2 + 0.08 * ((i * 53) % 5) / 5
    for peak, amp in ((0.24, 0.6), (0.57, 0.8), (0.83, 0.95)):
        d = abs((start + end) / 2 / DURATION - peak)
        if d < 0.07:
            base += amp * (1 - d / 0.07) ** 2
    return {"start": round(start, 2), "end": round(end, 2), "value": round(min(base, 1.0), 4)}


def _fused(heat: list[dict], replayed: list[dict]) -> list[dict]:
    """Fusion 0.6 capteur + 0.4 humains réels (même formule que F00C)."""
    replay_at = []
    for h in heat:
        mid = (h["start_sec"] + h["end_sec"]) / 2
        vals = [r["value"] for r in replayed if r["start"] <= mid < r["end"]]
        replay_at.append(vals[0] if vals else 0.0)
    max_r = max((v for v in replay_at), default=0.0) or 1.0
    out = []
    for h, r in zip(heat, replay_at):
        fused = 0.6 * h["attention_norm"] + 0.4 * (r / max_r)
        out.append({**h, "fused": round(fused, 4), "fused_norm": round(min(fused, 1.0), 4)})
    return out


def build_payload() -> dict:
    n = 100
    heat = [_bucket(i, n) for i in range(n)]
    replayed = [_replayed(i, 25) for i in range(25)]
    fused = _fused(heat, replayed)
    top = sorted(fused, key=lambda b: b["fused_norm"], reverse=True)
    candidates = []
    for rank, center_bucket in enumerate((top[0], top[12], top[30]), start=1):
        center = (center_bucket["start_sec"] + center_bucket["end_sec"]) / 2
        start = max(0.0, center - 17.5)
        candidates.append({
            "id": f"clip_0{rank}", "rank": rank,
            "start_sec": round(start, 2), "end_sec": round(start + 35.0, 2),
            "score": round(min(0.95, 0.55 + rank * 0.12 + center_bucket["fused_norm"] * 0.3), 4),
            "signal_type": "fused_peak_replayed_cross",
            "platforms": ["youtube_shorts", "tiktok", "instagram_reels", "x"],
        })
    return {
        "run_id": RUN_ID,
        "siege_id": "SOPHIE_RAIN_DEMO",
        "mode": "vod",
        "status": "full",
        "source": {"reference": "https://www.youtube.com/watch?v=qm3E3cchBmQ",
                   "platform": "youtube", "content_type": "video"},
        "heatmap": heat,
        "replayed_curve": replayed,
        "fused_heatmap": fused,
        "candidates": candidates,
        "pushed_at": "2026-09-12T23:00:00+00:00",
        "note": "seed_demo — payload synthétique conforme au contrat (démo dashboard)",
    }


def main() -> int:
    payload = build_payload()
    doc = {}
    if DATA_PATH.exists():
        try:
            doc = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            doc = {}
    doc["last_pushed_at"] = payload["pushed_at"]
    doc["last_run"] = payload
    doc.setdefault("runs", {})[RUN_ID] = {
        "siege_id": payload["siege_id"], "mode": payload["mode"],
        "status": payload["status"], "n_candidates": len(payload["candidates"]),
        "received_at": payload["pushed_at"],
    }
    doc["total_runs"] = len(doc["runs"])
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"SEED OK — {DATA_PATH} (run_id={RUN_ID}, {len(payload['candidates'])} candidats)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
