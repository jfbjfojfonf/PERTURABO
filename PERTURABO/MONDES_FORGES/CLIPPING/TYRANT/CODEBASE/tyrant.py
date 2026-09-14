"""
tyrant.py — TYRANT : La Frégate-Oracle (mode prospectif, forge CLIPPING)
========================================================================

Veille les Démons dominants hors campagne (wild clipping), cartographie
les océans bleus 1 couche, et nourrit ARCHIVUM/demons/ que F02_TYRANT_CAMP
lira pour les campagnes futures.

Pattern 3 phases :
  Phase 1 (prepare) : génère IN/tyrant_prompt.json (pour l'IRON)
  Phase 2 (IRON)    : le Warsmith copie le prompt, l'IRON scanne (yt-dlp
                      + transcripts) et écrit OUT/tyrant_eclaircissement.json
  Phase 3 (finalize): archive chaque Démon dans ARCHIVUM/demons/ + check-in

Usage:
  python tyrant.py --prepare --scan-list IN/scan_list.json
  python tyrant.py --finalize
  # Analyse automatique locale (sans IRON) :
  python tyrant.py --auto --scan-list IN/scan_list.json
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_TYRANT_DIR = os.path.dirname(_SCRIPT_DIR)
_FORGE_ROOT = os.path.dirname(_TYRANT_DIR)

sys.path.insert(0, os.path.join(_SCRIPT_DIR, "libs"))
from outlier_scorer import OutlierScorer
from emotion_classifier import EmotionClassifier
from blue_ocean_mapper import BlueOceanMapper
from demon_archivist import DemonArchivist

IN_DIR = os.path.join(_TYRANT_DIR, "IN")
OUT_DIR = os.path.join(_TYRANT_DIR, "OUT")
DEMONS_DIR = os.path.join(_FORGE_ROOT, "ARCHIVUM", "demons")

DEFAULT_CONFIG = {
    "outlier_threshold_x": 3,
    "niche_bending": True,
    "max_blue_ocean_depth": 1,
    "platforms": ["youtube", "tiktok", "instagram"],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_config() -> dict:
    path = os.path.join(IN_DIR, "tyrant_config.json")
    if os.path.exists(path):
        cfg = load_json(path)
        merged = dict(DEFAULT_CONFIG)
        merged.update(cfg or {})
        return merged
    save_json(path, DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)


def cmd_prepare(args):
    scan_list_path = args.scan_list
    if not os.path.isabs(scan_list_path):
        scan_list_path = os.path.join(_TYRANT_DIR, scan_list_path)
    if not os.path.exists(scan_list_path):
        print(f"[TYRANT] scan_list introuvable: {scan_list_path}")
        print("[TYRANT] Exemple: {\"channels\": [{\"url\": \"https://youtube.com/@...\"}]}")
        sys.exit(1)

    scan_list = load_json(scan_list_path)
    config = load_config()

    prompt = {
        "mission": "TYRANT (mode prospectif) — Veille Démon du wild clipping. "
                   "Pour chaque chaîne de la scan_list : récupère les métriques yt-dlp, "
                   "identifie les clips outliers (outlier_score > Xx), classe l'émotion dominante, "
                   "cartographie les océans bleus (1 couche max). "
                   "Écris OUT/tyrant_eclaircissement.json.",
        "scan_list": scan_list,
        "config": config,
        "regles_ocean_bleu": [
            "Profondeur océan bleu : 1 couche maximum (hérésie au-delà)",
            "Territoire saturé 'high' rejeté, 'low'/'medium' éligible",
            "Jamais de suggestion de sources alternatives (voir HERESIE)",
        ],
        "preuve_obligatoire": [
            "outlier_score quantitatif (views / baseline chaîne) pour chaque Démon",
            "dominant_emotion tracée (transcript ou titre)",
            "skeleton_extract : hook_type, loop_technique, structure_narrative",
        ],
        "output_attendu": "OUT/tyrant_eclaircissement.json (structure dans TYRANT/CODEBASE/TRACKING.md)",
        "heresies_interdites": [
            "Re-ciblage au-delà de 1 couche",
            "Démon identifié sans outlier_score",
            "Suggérer des sources alternatives à une future campagne",
        ],
    }
    save_json(os.path.join(IN_DIR, "tyrant_prompt.json"), prompt)

    eclaircissement = {
        "scan_id": now_iso(),
        "scanned_at": now_iso(),
        "demons_identified": [],
        "check_in_iw_custos": None,
    }
    save_json(os.path.join(OUT_DIR, "tyrant_eclaircissement.json"), eclaircissement)
    print(f"[TYRANT] Prompt IRON : {os.path.join(IN_DIR, 'tyrant_prompt.json')}")
    print("[TYRANT] Copier le prompt dans Claude sandbox -> OUT/tyrant_eclaircissement.json, puis --finalize")


def cmd_auto(args):
    """Éclaircissement local : aucun Démon sans preuve → scan minimal sans IRON."""
    scan_list_path = args.scan_list
    if not os.path.isabs(scan_list_path):
        scan_list_path = os.path.join(_TYRANT_DIR, scan_list_path)
    if not os.path.exists(scan_list_path):
        print(f"[TYRANT] scan_list introuvable: {scan_list_path}")
        sys.exit(1)
    scan_list = load_json(scan_list_path)
    config = load_config()

    demons = []
    for chan in scan_list.get("channels", []):
        clips = chan.get("clips") or chan.get("videos") or []
        for clip in clips:
            views = clip.get("views")
            baseline = clip.get("channel_avg_views") or chan.get("avg_views")
            scorer = OutlierScorer(threshold=config["outlier_threshold_x"])
            is_demon, score = scorer.is_demon(views, baseline)
            if not is_demon:
                continue
            classifier = EmotionClassifier()
            emotion = classifier.classify(title=clip.get("title"),
                                          transcript_text=clip.get("transcript_text"))
            mapper = BlueOceanMapper()
            oceans = mapper.map_for_emotion(emotion)
            demons.append({
                "demon_id": None,
                "demon_url": clip.get("url"),
                "platform": clip.get("platform") or chan.get("platform", "youtube"),
                "views": views,
                "outlier_score": score,
                "dominant_emotion": emotion,
                "dominant_engagement_type": clip.get("engagement_type"),
                "exploited_territories": [emotion] if emotion else [],
                "blue_ocean_unlocked": oceans,
                "skeleton_extract": {
                    "hook_type": clip.get("hook_type"),
                    "loop_technique": clip.get("loop_technique"),
                    "structure_narrative": clip.get("structure_narrative"),
                },
            })

    eclaircissement = {
        "scan_id": now_iso(),
        "scanned_at": now_iso(),
        "demons_identified": demons,
        "check_in_iw_custos": None,
        "iron_status": "auto",
    }
    save_json(os.path.join(OUT_DIR, "tyrant_eclaircissement.json"), eclaircissement)
    print(f"[TYRANT] --auto : {len(demons)} Démon(s) identifié(s) (outlier > {config['outlier_threshold_x']}x)")


def cmd_finalize(args):
    path = os.path.join(OUT_DIR, "tyrant_eclaircissement.json")
    if not os.path.exists(path):
        print("[TYRANT] OUT/tyrant_eclaircissement.json absent — lancer --prepare puis IRON, ou --auto")
        sys.exit(1)

    eclaircissement = load_json(path)
    config = load_config()

    # Hérésie guard : profondeur > 1 → clamp
    mapper = BlueOceanMapper()
    for demon in eclaircissement.get("demons_identified", []):
        demon["blue_ocean_unlocked"] = mapper.enforce_max_depth(
            demon.get("blue_ocean_unlocked", [])
        )

    archivist = DemonArchivist(_FORGE_ROOT)
    written = archivist.archive(eclaircissement)
    eclaircissement["check_in_iw_custos"] = now_iso()
    save_json(path, eclaircissement)

    custos = os.path.join(_FORGE_ROOT, "IW_CUSTOS.py")
    if os.path.exists(custos):
        subprocess.run([sys.executable, custos, "--mode", "check-in",
                        "--frigate", "TYRANT", "--output", path],
                       capture_output=True, text=True, timeout=30)

    print(f"[TYRANT] Finalize : {len(written)} Démon(s) archivé(s) dans ARCHIVUM/demons/")
    for w in written:
        print(f"  {w}")
    print("[TYRANT] Check-in IW_CUSTOS — statut TYRANT = done")


def main():
    parser = argparse.ArgumentParser(description="TYRANT — Oracle prospectif (veille Démon)")
    parser.add_argument("--prepare", action="store_true", help="Phase 1 : prompt IRON")
    parser.add_argument("--auto", action="store_true", help="Éclaircissement auto local (sans IRON)")
    parser.add_argument("--finalize", action="store_true", help="Phase 3 : archive + check-in")
    parser.add_argument("--scan-list", default="IN/scan_list.json")
    args = parser.parse_args()

    if args.prepare:
        cmd_prepare(args)
    elif args.auto:
        cmd_auto(args)
    elif args.finalize:
        cmd_finalize(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
