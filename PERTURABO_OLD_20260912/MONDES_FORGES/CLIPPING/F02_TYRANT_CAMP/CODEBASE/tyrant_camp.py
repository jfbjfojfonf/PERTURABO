"""
tyrant_camp.py — F02_TYRANT_CAMP : La Frégate-Statège (forge CLIPPING)
======================================================================

Frégate stratège de la Porte 1. Mode RÉACTIF : prend le source_specimen.json
de F01_SCOUT et rend un verdict GO/NO-GO + identification océan bleu
(sur la MÊME source que le Démon — jamais au-delà de 1 couche).

Pattern 3 phases :
  Phase 1 (prepare) : génère IN/tyrant_camp_prompt.json (pour l'IRON)
  Phase 2 (IRON)    : le Warsmith copie le prompt, l'IRON écrit OUT/campaign_verdict.json
  Phase 3 (finalize): validation + check-in IW_CUSTOS + copie vers ARCHIVUM/campaign/

Usage:
  python tyrant_camp.py --prepare --specimen ../F01_SCOUT/OUT/source_specimen.json
  python tyrant_camp.py --finalize
  # Analyse automatique locale (sans IRON) :
  python tyrant_camp.py --auto --specimen ../F01_SCOUT/OUT/source_specimen.json
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F02_DIR = os.path.dirname(_SCRIPT_DIR)
_FORGE_ROOT = os.path.dirname(_F02_DIR)

sys.path.insert(0, os.path.join(_SCRIPT_DIR, "libs"))
from blue_ocean_finder import BlueOceanFinder
from skeleton_extractor import SkeletonExtractor
from fit_scorer import FitScorer

OUT_DIR = os.path.join(_F02_DIR, "OUT")
IN_DIR = os.path.join(_F02_DIR, "IN")
CAMPAIGN_DIR = os.path.join(_FORGE_ROOT, "ARCHIVUM", "campaign")
DEMONS_DIR = os.path.join(_FORGE_ROOT, "ARCHIVUM", "demons")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _specimen_campaign_id(specimen: dict) -> str:
    return specimen.get("campaign_id") or "campaign_unknown"


def cmd_prepare(args):
    """Phase 1 — génère le prompt IRON pour le verdict."""
    specimen_path = args.specimen
    if not os.path.isabs(specimen_path):
        specimen_path = os.path.join(_FORGE_ROOT, specimen_path)
    if not os.path.exists(specimen_path):
        print(f"[F02] specimen introuvable: {specimen_path}")
        sys.exit(1)

    specimen = load_json(specimen_path)
    reference = specimen.get("reference_clip", {})
    campaign_id = _specimen_campaign_id(specimen)

    # Océans bleus candidats (depuis ARCHIVUM/demons/)
    finder = BlueOceanFinder(_FORGE_ROOT)
    oceans = finder.find_for_campaign()

    # Pré-squelette
    extractor = SkeletonExtractor(_FORGE_ROOT)
    skeleton = extractor.preskeleton(reference)

    # Fit indicatif
    platform = args.platform or "youtube"
    market = args.market or "us_young_english"
    cartographie_path = os.path.join(_FORGE_ROOT, "F00_CAPTEURS", "OUT", "cartographie.json")
    cartographie = None
    if os.path.exists(cartographie_path):
        cartographie = load_json(cartographie_path)
    scorer = FitScorer(_FORGE_ROOT)
    fit = scorer.score(platform, market, cartographie)

    prompt = {
        "mission": "F02_TYRANT_CAMP — Verdict de campagne (IRON sandbox). "
                   "Analyse le specimen, le squelette du clip de référence, les Démons, "
                   "les océans bleus, le fit plateforme/marché, la saturation. "
                   "Rends le verdict GO/NO-GO avec preuve (chaque assertion tracée). "
                   "Écris OUT/campaign_verdict.json.",
        "campaign_id": campaign_id,
        "platform_target": platform,
        "market_target": market,
        "specimen": specimen,
        "reference_clip": reference,
        "preskeleton": skeleton,
        "blue_ocean_candidates": oceans,
        "fit_indicatif": fit,
        "cartographie": cartographie,
        "regles_ocean_bleu": [
            "Profondeur océan bleu : 1 couche maximum (hérésie au-delà)",
            "Re-ciblage uniquement sur la même source que la campagne",
            "Saturation low/medium éligible, high rejeté",
        ],
        "output_attendu": "OUT/campaign_verdict.json (structure dans F02_TYRANT_CAMP/CODEBASE/TRACKING.md)",
        "heresies_interdites": [
            "Re-ciblage au-delà de 1 couche",
            "Suggérer des sources alternatives (assets = forteresse fermée)",
            "Verdict sans preuve",
            "Ignorer le fit plateforme/marché",
        ],
    }
    save_json(os.path.join(IN_DIR, "tyrant_camp_prompt.json"), prompt)

    # Pré-remplir le verdict (état pending)
    verdict = {
        "campaign_id": campaign_id,
        "verdict": None,
        "verdict_justification": None,
        "reference_skeleton": skeleton,
        "demon_analysis": {
            "demon_id": None,
            "dominant_emotion": skeleton.get("emotion_dominante"),
            "exploited_territories": [],
            "blue_ocean_unlocked": oceans,
        },
        "direct_analysis": fit,
        "check_in_iw_custos": None,
        "iron_status": "pending",
    }
    save_json(os.path.join(OUT_DIR, "campaign_verdict.json"), verdict)

    print(f"[F02] Prompt IRON : {os.path.join(IN_DIR, 'tyrant_camp_prompt.json')}")
    print(f"[F02] {len(oceans)} océans bleus candidats depuis ARCHIVUM/demons/")
    print("[F02] Copier le prompt dans Claude sandbox -> OUT/campaign_verdict.json, puis --finalize")


def cmd_auto(args):
    """Verdict automatique local : GO par défaut si specimen valide, hérésie si aucun."""
    specimen_path = args.specimen
    if not os.path.isabs(specimen_path):
        specimen_path = os.path.join(_FORGE_ROOT, specimen_path)
    specimen = load_json(specimen_path)

    campaign_id = _specimen_campaign_id(specimen)
    reference = specimen.get("reference_clip", {})
    finder = BlueOceanFinder(_FORGE_ROOT)
    oceans = finder.find_for_campaign()
    extractor = SkeletonExtractor(_FORGE_ROOT)
    skeleton = extractor.preskeleton(reference)
    scorer = FitScorer(_FORGE_ROOT)
    fit = scorer.score(args.platform, args.market)

    assets_ok = len(specimen.get("assets", [])) >= 1
    verdict = {
        "campaign_id": campaign_id,
        "verdict": "GO" if assets_ok else "NO-GO",
        "verdict_justification": (
            "GO — assets fournis par la campagne présents, verdict provisoire "
            "(IRON sandbox requis pour validation finale)"
            if assets_ok else
            "NO-GO — aucun asset dans le specimen (strict-source violé)"
        ),
        "reference_skeleton": skeleton,
        "demon_analysis": {
            "demon_id": None,
            "dominant_emotion": skeleton.get("emotion_dominante"),
            "exploited_territories": [],
            "blue_ocean_unlocked": oceans,
        },
        "direct_analysis": fit,
        "check_in_iw_custos": now_iso(),
        "iron_status": "auto",
    }
    save_json(os.path.join(OUT_DIR, "campaign_verdict.json"), verdict)
    print(f"[F02] --auto : verdict {verdict['verdict']} écrit (océans bleus: {len(oceans)})")


def cmd_finalize(args):
    """Phase 3 — valide le verdict, copie vers ARCHIVUM/campaign/, check-in."""
    verdict_path = os.path.join(OUT_DIR, "campaign_verdict.json")
    if not os.path.exists(verdict_path):
        print("[F02] OUT/campaign_verdict.json absent — lancer --prepare puis IRON, ou --auto")
        sys.exit(1)

    verdict = load_json(verdict_path)
    if verdict.get("verdict") not in ("GO", "NO-GO"):
        print("[F02] verdict invalide (doit être GO ou NO-GO) — attendre l'IRON")
        sys.exit(1)

    for ocean in verdict.get("demon_analysis", {}).get("blue_ocean_unlocked", []):
        depth = ocean.get("blue_ocean_depth")
        if depth is not None and depth != 1:
            print(f"[F02] HÉRÉSIE : blue_ocean_depth={depth} > 1 — rejeter cet océan")
            ocean["blue_ocean_depth"] = 1
            ocean["_rejected_depth_violation"] = True

    verdict["check_in_iw_custos"] = now_iso()
    save_json(verdict_path, verdict)

    # Copie canonique vers ARCHIVUM/campaign/
    os.makedirs(CAMPAIGN_DIR, exist_ok=True)
    with open(os.path.join(CAMPAIGN_DIR, "verdict.json"), "w", encoding="utf-8") as f:
        json.dump(verdict, f, indent=2, ensure_ascii=False)
    skeleton = verdict.get("reference_skeleton", {})
    with open(os.path.join(CAMPAIGN_DIR, "reference_skeleton.json"), "w", encoding="utf-8") as f:
        json.dump(skeleton, f, indent=2, ensure_ascii=False)

    # scout_report.md mentionné dans le TRACKING est généré par F01 — ici le verdict md
    report_path = os.path.join(OUT_DIR, "verdict_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# Verdict campagne {verdict.get('campaign_id')}\n\n"
                f"- Verdict : **{verdict.get('verdict')}**\n"
                f"- Justification : {verdict.get('verdict_justification', 'N/A')}\n"
                f"- Océans bleus : {len(verdict.get('demon_analysis', {}).get('blue_ocean_unlocked', []))}\n")

    custos = os.path.join(_FORGE_ROOT, "IW_CUSTOS.py")
    if os.path.exists(custos):
        subprocess.run([sys.executable, custos, "--mode", "check-in",
                        "--frigate", "F02", "--output", verdict_path],
                       capture_output=True, text=True, timeout=30)
    print(f"[F02] Finalize : verdict {verdict['verdict']} — copié vers ARCHIVUM/campaign/verdict.json")
    print("[F02] Check-in IW_CUSTOS — statut F02 = done, verdict disponible Porte 1")


def main():
    parser = argparse.ArgumentParser(description="F02_TYRANT_CAMP — Verdict de campagne")
    parser.add_argument("--prepare", action="store_true", help="Phase 1 : prompt IRON")
    parser.add_argument("--auto", action="store_true", help="Verdict auto local (sans IRON)")
    parser.add_argument("--finalize", action="store_true", help="Phase 3 : validation + check-in")
    parser.add_argument("--specimen", default="F01_SCOUT/OUT/source_specimen.json")
    parser.add_argument("--platform", default="youtube")
    parser.add_argument("--market", default="us_young_english")
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
