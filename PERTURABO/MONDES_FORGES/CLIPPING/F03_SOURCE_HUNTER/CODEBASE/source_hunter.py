"""
source_hunter.py — F03_SOURCE_HUNTER : La Sélection de la Seam (forge CLIPPING)
===============================================================================

Frégate de sélection (Porte 3). Prend les N angles forgés par ANGLESMITH
(Porte 2) et identifie pour chaque angle la MEILLEURE vidéo longue des
assets de la campagne (strict-source, jamais ailleurs) + les segments
pertinents dans cette vidéo (directives — la coupe reste à D-F02 d'OMNIS_WATCH).

Pattern 3 phases :
  Phase 1 (prepare) : génère IN/source_hunter_prompt.json (pour l'IRON)
  Phase 2 (IRON)    : le Warsmith copie le prompt, l'IRON écrit
                      OUT/source_specimen_<angle_id>.json (un par angle)
  Phase 3 (finalize): validation cohérence + OUT/source_summary.md
                      + check-in IW_CUSTOS (F03 -> specimens_selected)

Usage:
  python source_hunter.py --prepare --angles ../F02_TYRANT_CAMP/OUT/angles.json
  python source_hunter.py --auto --angles ../F02_TYRANT_CAMP/OUT/angles.json
  python source_hunter.py --finalize
"""

import argparse
import glob
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F03_DIR = os.path.dirname(_SCRIPT_DIR)
_FORGE_ROOT = os.path.dirname(_F03_DIR)

sys.path.insert(0, os.path.join(_SCRIPT_DIR, "libs"))
from transcript_loader import TranscriptLoader
from duration_guard import DurationGuard
from segment_matcher import SegmentMatcher

OUT_DIR = os.path.join(_F03_DIR, "OUT")
IN_DIR = os.path.join(_F03_DIR, "IN")
CAMPAIGN_DIR = os.path.join(_FORGE_ROOT, "ARCHIVUM", "campaign")
F01_OUT = os.path.join(_FORGE_ROOT, "F01_SCOUT", "OUT")
F02_OUT = os.path.join(_FORGE_ROOT, "F02_TYRANT_CAMP", "OUT")
LIBER_PATH = os.path.join(_FORGE_ROOT, "liber_clipping.json")

ANGLES_CANDIDATES = [
    os.path.join(F02_OUT, "angles.json"),
    os.path.join(_FORGE_ROOT, "ANGLESMITH", "OUT", "angles.json"),
]


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------
# Résolution des entrées (strict-source)
# ----------------------------------------------------------------------
def find_angles_path() -> str:
    for candidate in ANGLES_CANDIDATES:
        if os.path.exists(candidate):
            return candidate
    print("[F03] angles.json introuvable (F02_TYRANT_CAMP/OUT ou ANGLESMITH/OUT)")
    print("[F03] Lancer ANGLESMITH --finalize d'abord (Porte 2)")
    sys.exit(1)


def load_f01_specimen() -> dict:
    path = os.path.join(F01_OUT, "source_specimen.json")
    if not os.path.exists(path):
        print(f"[F03] F01 specimen introuvable: {path}")
        sys.exit(1)
    return load_json(path)


def load_verdict() -> dict:
    for path in (os.path.join(CAMPAIGN_DIR, "verdict.json"),
                 os.path.join(F02_OUT, "campaign_verdict.json")):
        if os.path.exists(path):
            return load_json(path)
    print("[F03] verdict introuvable (ARCHIVUM/campaign/verdict.json ou F02 OUT)")
    return {}


def warsmith_targets(args) -> tuple[str, str]:
    """Plateforme + marché : args CLI prioritaire, sinon liber_clipping.json."""
    platform = getattr(args, "platform", None)
    market = getattr(args, "market", None)
    if not platform or not market:
        if os.path.exists(LIBER_PATH):
            inputs = load_json(LIBER_PATH).get("inputs_warsmith", {})
            platform = platform or inputs.get("platform_target")
            market = market or inputs.get("market_target")
    return platform or "youtube", market or "unknown"


def angles_from_file(path: str) -> list[dict]:
    data = load_json(path)
    angles = data.get("angles", [])
    if not angles:
        print(f"[F03] angles.json vide: {path}")
        sys.exit(1)
    return angles


# ----------------------------------------------------------------------
# Phase 1 — prepare (prompt IRON)
# ----------------------------------------------------------------------
def cmd_prepare(args):
    specimen = load_f01_specimen()
    verdict = load_verdict()
    angles = angles_from_file(find_angles_path())
    platform, market = warsmith_targets(args)
    guard = DurationGuard(_FORGE_ROOT)
    lo, hi = guard.bounds(platform)

    prompt = {
        "mission": "F03_SOURCE_HUNTER (Porte 3) — Sélection des sources. "
                   "Pour chaque angle, choisis dans les assets de la campagne "
                   "(strict-source, règle C1) la meilleure vidéo longue + les "
                   "segments pertinents (directives pour D-F02 d'OMNIS_WATCH). "
                   "Écris OUT/source_specimen_<angle_id>.json (un par angle).",
        "campaign_id": specimen.get("campaign_id"),
        "platform_target": platform,
        "market_target": market,
        "duration_fourchette_sec": [lo, hi],
        "angles": angles,
        "assets": [
            {
                "asset_id": a.get("asset_id"),
                "url": a.get("url"),
                "title": a.get("title"),
                "duration_sec": a.get("duration_sec"),
                "transcript_available": a.get("transcript_available", False),
                "transcript_path": a.get("transcript_path"),
            }
            for a in specimen.get("assets", [])
        ],
        "verdict": verdict,
        "output_attendu": "OUT/source_specimen_<angle_id>.json "
                          "(schéma : F03_SOURCE_HUNTER/CODEBASE/TRACKING.md)",
        "regles": [
            f"Chaque segment doit rester dans [{lo}s, {hi}s] (plateforme {platform})",
            "Si l'angle est en zone blue_ocean -> blue_ocean_reframe_applied = true",
            "Le choix doit être justifié par le transcript (extracted_text_snippet)",
            "Rationale qualitative pour asset_selected et chaque segment",
        ],
        "heresies_interdites": [
            "Sélectionner un asset qui n'est pas dans les assets de F01",
            "Couper/monter la vidéo (boulot de D-F02 OMNIS_WATCH)",
            "Segments hors fourchette plateforme",
            "Ignorer blue_ocean_reframe_applied quand l'angle est en océan bleu",
        ],
    }
    save_json(os.path.join(IN_DIR, "source_hunter_prompt.json"), prompt)
    print(f"[F03] Prompt IRON : {os.path.join(IN_DIR, 'source_hunter_prompt.json')}")
    print(f"[F03] {len(angles)} angles, {len(specimen.get('assets', []))} assets, "
          f"fourchette [{lo}s, {hi}s] ({platform})")
    print("[F03] Copier le prompt dans Claude sandbox -> "
          "OUT/source_specimen_<angle_id>.json, puis --finalize")


# ----------------------------------------------------------------------
# Phase 2 — auto (analyse locale sans IRON)
# ----------------------------------------------------------------------
def cmd_auto(args):
    specimen = load_f01_specimen()
    angles = angles_from_file(find_angles_path())
    platform, market = warsmith_targets(args)
    campaign_id = specimen.get("campaign_id", "campaign_unknown")

    loader = TranscriptLoader(CAMPAIGN_DIR)
    guard = DurationGuard(_FORGE_ROOT)
    matcher = SegmentMatcher(loader, guard)

    if not loader.available():
        print("[F03] AVERTISSEMENT: aucun transcript dans ARCHIVUM/campaign/transcripts/ "
              "— l'IRON devra affiner (ou lancer F01 --auto --transcribe)")

    assets = specimen.get("assets", [])
    for angle in angles:
        asset = matcher.best_asset_for_angle(angle, assets, platform)
        segments = matcher.suggested_segments(angle, asset, platform)

        is_blue = angle.get("zone") == "blue_ocean"
        specimen_out = {
            "campaign_id": campaign_id,
            "angle_id": angle.get("angle_id"),
            "angle": {
                "angle_family": angle.get("angle_family"),
                "emotion_mode": angle.get("emotion_mode"),
                "engagement_type": angle.get("engagement_type"),
                "reframe_dim": angle.get("reframe_dim"),
                "zone": angle.get("zone"),
                "territory": angle.get("territory"),
            },
            "asset_selected": {
                "asset_id": asset.get("asset_id"),
                "url": asset.get("url"),
                "title": asset.get("title"),
                "duration_sec": asset.get("duration_sec"),
                "rationale": "Meilleur score fenêtres transcript pour cet angle "
                             "(auto) — l'IRON affine en Phase 2" if segments else
                             "Transcript indisponible — asset long par défaut, "
                             "l'IRON affine en Phase 2",
            },
            "suggested_segments": segments,
            "blue_ocean_reframe_applied": bool(is_blue),
            "platform_fit": None,
            "market_fit": None,
            "selection_mode": "auto",
            "check_in_iw_custos": None,
        }
        save_json(os.path.join(OUT_DIR, f"source_specimen_{angle.get('angle_id')}.json"),
                  specimen_out)
        print(f"[F03] --auto : {angle.get('angle_id')} -> "
              f"{asset.get('asset_id')} ({len(segments)} segment(s))")


# ----------------------------------------------------------------------
# Phase 3 — finalize (validation + check-in)
# ----------------------------------------------------------------------
def _validate_specimen(specimen: dict, angles: list[dict], assets: list[dict],
                       platform: str, guard: DurationGuard) -> list[str]:
    errors = []
    angle = next((a for a in angles if a.get("angle_id") == specimen.get("angle_id")), {})
    asset_urls = [a.get("url") for a in assets]

    if not specimen.get("angle_id"):
        errors.append("angle_id manquant")

    selected = specimen.get("asset_selected", {})
    if not selected.get("url"):
        errors.append(f"{specimen.get('angle_id')}: asset_selected.url manquant")
    elif selected.get("url") not in asset_urls:
        errors.append(f"{specimen.get('angle_id')}: HERESIE — asset {selected.get('url')} "
                      f"hors des assets de la campagne")

    for seg in specimen.get("suggested_segments", []):
        ok, msg = guard.validate(seg.get("start_sec", 0), seg.get("end_sec", 0), platform)
        if not ok:
            errors.append(f"{specimen.get('angle_id')}: {msg}")

    if angle.get("zone") == "blue_ocean" and not specimen.get("blue_ocean_reframe_applied"):
        errors.append(f"{specimen.get('angle_id')}: blue_ocean_reframe_applied doit être true "
                      f"(angle en zone océan bleu)")
    if angle.get("zone") != "blue_ocean" and specimen.get("blue_ocean_reframe_applied"):
        errors.append(f"{specimen.get('angle_id')}: blue_ocean_reframe_applied=true "
                      f"mais angle hors océan bleu")
    return errors


def cmd_finalize(args):
    paths = sorted(glob.glob(os.path.join(OUT_DIR, "source_specimen_*.json")))
    if not paths:
        print("[F03] OUT/source_specimen_*.json absent — lancer --prepare puis IRON, ou --auto")
        sys.exit(1)

    specimen_f01 = load_f01_specimen()
    angles = angles_from_file(find_angles_path())
    platform, _ = warsmith_targets(args)
    guard = DurationGuard(_FORGE_ROOT)
    assets = specimen_f01.get("assets", [])

    errors = []
    for path in paths:
        errors += _validate_specimen(load_json(path), angles, assets, platform, guard)
    if errors:
        print("[F03] Specimens invalides :")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # source_summary.md
    lines = [
        "# F03_SOURCE_HUNTER — Synthèse des sources",
        "",
        f"- Campagne : {specimen_f01.get('campaign_id', 'N/A')}",
        f"- Plateforme : {platform}",
        f"- Specimens validés : {len(paths)}",
        "",
        "| Angle | Asset | Segments | Durée fenêtres | Océan bleu |",
        "|---|---|---|---|---|",
    ]
    for path in paths:
        s = load_json(path)
        segs = s.get("suggested_segments", [])
        durations = ", ".join(f"{seg.get('duration_sec', '?')}s" for seg in segs) or "—"
        blue = "oui" if s.get("blue_ocean_reframe_applied") else "non"
        lines.append(f"| {s.get('angle_id')} | {s.get('asset_selected', {}).get('asset_id')} "
                     f"| {len(segs)} | {durations} | {blue} |")

    summary_path = os.path.join(OUT_DIR, "source_summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    for path in paths:
        s = load_json(path)
        s["check_in_iw_custos"] = now_iso()
        save_json(path, s)

    custos = os.path.join(_FORGE_ROOT, "IW_CUSTOS.py")
    if os.path.exists(custos):
        subprocess.run([sys.executable, custos, "--mode", "check-in",
                        "--frigate", "F03", "--output", summary_path],
                       capture_output=True, text=True, timeout=30)
    print(f"[F03] Finalize : {len(paths)} specimens validés — {summary_path}")
    print("[F03] Check-in IW_CUSTOS — fleet_status -> specimens_selected")
    print("[F03] OUT prêt pour F04_COPYWRITER (text_payloads) et F05_PACKAGER")


def main():
    parser = argparse.ArgumentParser(description="F03_SOURCE_HUNTER — La Sélection de la Seam")
    parser.add_argument("--prepare", action="store_true", help="Phase 1 : prompt IRON")
    parser.add_argument("--auto", action="store_true", help="Sélection auto locale (sans IRON)")
    parser.add_argument("--finalize", action="store_true", help="Phase 3 : validation + check-in")
    parser.add_argument("--angles", default=None,
                        help="Chemin vers angles.json (défaut: F02/OUT/angles.json)")
    parser.add_argument("--platform", default=None, help="Plateforme cible (override)")
    parser.add_argument("--market", default=None, help="Marché cible (override)")
    args = parser.parse_args()

    if args.angles:
        ANGLES_CANDIDATES.insert(0, args.angles)

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
