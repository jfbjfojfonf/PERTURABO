"""
pattern_capture.py — CAPTEURS : Détection de patterns viraux
==============================================================

Analyse les vidéos capturées par iron_sentinel.py et détecte les patterns viraux.
Un pattern viral = une vidéo dont l'Outlier Score dépasse un seuil.

Seuils :
  - Outlier Score > 10.0 → SIGNAL ROUGE (vidéo virale massive)
  - Outlier Score > 3.0  → SIGNAL JAUNE (vidéo qui performe bien)
  - Outlier Score < 3.0  → Pas de signal

Usage:
  python pattern_capture.py --sweep CAPTEURS/OUT/signals/sweep_xxx.json
  python pattern_capture.py --analyze ARCHIVUM/transcripts/
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CAPTEURS_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_CAPTEURS_DIR)
_CAPTEURS_SIGNALS = os.path.join(_CAPTEURS_DIR, "OUT", "signals")
_ARCHIVUM_TRANSCRIPTS = os.path.join(_PROJECT_ROOT, "ARCHIVUM", "transcripts")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def classify_signal(outlier_score: float) -> str | None:
    """Classifie un signal selon l'Outlier Score."""
    if outlier_score is None:
        return None
    if outlier_score > 10.0:
        return "ROUGE"
    elif outlier_score > 3.0:
        return "JAUNE"
    return None


def analyze_sweep(sweep_path: str) -> dict:
    """
    Analyse un rapport de sweep et enrichit les signaux avec des patterns.
    """
    with open(sweep_path, "r", encoding="utf-8") as f:
        sweep = json.load(f)

    signals = sweep.get("signals", [])
    enriched_signals = []

    for signal in signals:
        outlier = signal.get("outlier_score")
        level = classify_signal(outlier)

        if level:
            enriched = signal.copy()
            enriched["signal_level"] = level
            enriched["pattern_type"] = _identify_pattern_type(signal)
            enriched["analyzed_at"] = now_iso()
            enriched_signals.append(enriched)

    # Trier par outlier_score décroissant
    enriched_signals.sort(key=lambda s: s.get("outlier_score", 0), reverse=True)

    return {
        "sweep_id": sweep.get("sweep_id"),
        "analyzed_at": now_iso(),
        "total_signals": len(enriched_signals),
        "red_signals": sum(1 for s in enriched_signals if s["signal_level"] == "ROUGE"),
        "yellow_signals": sum(1 for s in enriched_signals if s["signal_level"] == "JAUNE"),
        "signals": enriched_signals,
    }


def _identify_pattern_type(signal: dict) -> str:
    """Identifie le type de pattern viral basé sur les métadonnées."""
    title = signal.get("title", "").lower()
    view_count = signal.get("view_count", 0)
    outlier = signal.get("outlier_score", 0)

    # Heuristiques simples
    if any(word in title for word in ["top", "classement", "best", "worst"]):
        return "liste_ordonnee"
    elif any(word in title for word in ["expliqué", "explained", "secret", "caché"]):
        return "revelation"
    elif any(word in title for word in ["pourquoi", "why", "comment"]):
        return "question_ouverte"
    elif outlier > 20:
        return "outlier_extreme"
    else:
        return "format_standard"


def analyze_archivum() -> dict:
    """
    Analyse tous les transcripts de l'ARCHIVUM et identifie les patterns globaux.
    Utile pour détecter des tendances sur plusieurs vidéos.
    """
    if not os.path.exists(_ARCHIVUM_TRANSCRIPTS):
        return {"error": "ARCHIVUM/transcripts/ vide ou inexistant"}

    files = sorted(Path(_ARCHIVUM_TRANSCRIPTS).glob("*.json"))
    all_videos = []
    red_count = 0
    yellow_count = 0

    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            outlier = data.get("outlier_score")
            level = classify_signal(outlier)

            if level:
                all_videos.append({
                    "video_id": data.get("video_id"),
                    "title": data.get("title"),
                    "channel": data.get("channel"),
                    "outlier_score": outlier,
                    "signal_level": level,
                    "pattern_type": _identify_pattern_type({"title": data.get("title", ""), "outlier_score": outlier}),
                })
                if level == "ROUGE":
                    red_count += 1
                else:
                    yellow_count += 1
        except (json.JSONDecodeError, KeyError):
            continue

    # Trier par outlier_score
    all_videos.sort(key=lambda v: v.get("outlier_score", 0), reverse=True)

    # Compter les patterns
    pattern_counts = {}
    for v in all_videos:
        pt = v.get("pattern_type", "unknown")
        pattern_counts[pt] = pattern_counts.get(pt, 0) + 1

    return {
        "analyzed_at": now_iso(),
        "total_transcripts": len(files),
        "total_signals": len(all_videos),
        "red_signals": red_count,
        "yellow_signals": yellow_count,
        "pattern_distribution": pattern_counts,
        "top_signals": all_videos[:10],
    }


def main():
    parser = argparse.ArgumentParser(description="CAPTEURS — Pattern Capture")
    parser.add_argument("--sweep", default=None, help="Chemin vers un rapport de sweep")
    parser.add_argument("--analyze", action="store_true", help="Analyser tout l'ARCHIVUM")
    args = parser.parse_args()

    if args.sweep:
        result = analyze_sweep(args.sweep)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.analyze:
        result = analyze_archivum()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("Usage: python pattern_capture.py --sweep <path> ou --analyze")
        sys.exit(1)


if __name__ == "__main__":
    main()
