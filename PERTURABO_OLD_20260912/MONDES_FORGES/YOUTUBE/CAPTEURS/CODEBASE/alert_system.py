"""
alert_system.py — CAPTEURS : Système d'alerte pour le TYRANT
=============================================================

Génère les alertes que le TYRANT lira à la prochaine Porte 1.
Synthétise les signaux des Capteurs en un rapport lisible par l'Oracle.

Usage:
  python alert_system.py
  python alert_system.py --sweep CAPTEURS/OUT/signals/sweep_xxx.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CAPTEURS_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_CAPTEURS_DIR)
_CAPTEURS_SIGNALS = os.path.join(_CAPTEURS_DIR, "OUT", "signals")
_CAPTEURS_OUT = os.path.join(_CAPTEURS_DIR, "OUT")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_latest_sweep() -> str | None:
    """Trouve le rapport de sweep le plus récent."""
    if not os.path.exists(_CAPTEURS_SIGNALS):
        return None
    files = sorted([f for f in os.listdir(_CAPTEURS_SIGNALS) if f.endswith(".json")], reverse=True)
    if not files:
        return None
    return os.path.join(_CAPTEURS_SIGNALS, files[0])


def generate_alert(sweep_path: str = None) -> dict:
    """
    Génère un rapport d'alerte synthétisé pour le TYRANT.
    Le TYRANT lira ce fichier à la prochaine Porte 1.
    """
    if sweep_path is None:
        sweep_path = find_latest_sweep()

    if not sweep_path or not os.path.exists(sweep_path):
        return {
            "alert_id": f"alert_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            "generated_at": now_iso(),
            "status": "NO_SIGNAL",
            "message": "Aucun signal des Capteurs — première chasse ou Capteurs inactifs.",
            "signals": [],
        }

    with open(sweep_path, "r", encoding="utf-8") as f:
        sweep = json.load(f)

    signals = sweep.get("signals", [])
    red_signals = [s for s in signals if s.get("signal_level") == "ROUGE"]
    yellow_signals = [s for s in signals if s.get("signal_level") == "JAUNE"]

    # Synthétiser le message pour le TYRANT
    message_parts = []
    if red_signals:
        message_parts.append(f"🔴 {len(red_signals)} signal(s) ROUGE — vidéos virales massives détectées")
    if yellow_signals:
        message_parts.append(f"🟡 {len(yellow_signals)} signal(s) JAUNE — vidéos qui performant bien")
    if not signals:
        message_parts.append("Aucun signal significatif lors du dernier sweep.")

    # Lister les chaînes avec des signaux
    channels_with_signals = list(set(s.get("channel", "Inconnu") for s in signals))

    # Top 5 des signaux les plus forts
    top_signals = sorted(signals, key=lambda s: s.get("outlier_score", 0), reverse=True)[:5]

    alert = {
        "alert_id": f"alert_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "generated_at": now_iso(),
        "source_sweep": os.path.basename(sweep_path),
        "sweep_date": sweep.get("sweep_date"),
        "status": "SIGNALS_DETECTED" if signals else "NO_SIGNAL",
        "message": " | ".join(message_parts),
        "channels_with_signals": channels_with_signals,
        "red_count": len(red_signals),
        "yellow_count": len(yellow_signals),
        "top_signals": top_signals,
        "new_transcripts_archived": sweep.get("new_transcripts_archived", 0),
    }

    # Sauvegarder l'alerte
    os.makedirs(_CAPTEURS_OUT, exist_ok=True)
    alert_path = os.path.join(_CAPTEURS_OUT, "latest_alert.json")
    with open(alert_path, "w", encoding="utf-8") as f:
        json.dump(alert, f, ensure_ascii=False, indent=2)

    print(f"[ALERT] Alerte générée: {alert_path}")
    print(f"[ALERT] Status: {alert['status']}")
    print(f"[ALERT] Message: {alert['message']}")
    if top_signals:
        print(f"[ALERT] Top signal: {top_signals[0]['title']} (Outlier: {top_signals[0]['outlier_score']})")

    return alert


def main():
    parser = argparse.ArgumentParser(description="CAPTEURS — Alert System")
    parser.add_argument("--sweep", default=None, help="Chemin vers un rapport de sweep spécifique")
    args = parser.parse_args()

    generate_alert(args.sweep)


if __name__ == "__main__":
    main()
