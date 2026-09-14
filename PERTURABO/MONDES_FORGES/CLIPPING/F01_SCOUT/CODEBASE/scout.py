"""
scout.py — F01_SCOUT : La Reconnaissance de Fer (forge CLIPPING)
================================================================

Frégate d'acquisition. Inventorie les assets fournis par la campagne
(directive.md + reference_clip.json) et produit OUT/source_specimen.json
consommé par F02_TYRANT_CAMP (Porte 1) et F03_SOURCE_HUNTER (Porte 3).

Pattern 3 phases :
  Phase 1 (prepare) : parse directive.md -> IN/scout_prompt.json (pour l'IRON)
  Phase 2 (IRON)    : le Warsmith copie le prompt dans Claude sandbox,
                      l'IRON écrit OUT/source_specimen.json
  Phase 3 (finalize): validation cohérence + check-in IW_CUSTOS + libérer

Usage:
  python scout.py --prepare --directive ../ARCHIVUM/campaign/directive.md
  python scout.py --finalize
  # Alternative (sans IRON) : analyse automatique + enrichissement local
  python scout.py --auto --directive ../ARCHIVUM/campaign/directive.md
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F01_DIR = os.path.dirname(_SCRIPT_DIR)
_FORGE_ROOT = os.path.dirname(_F01_DIR)

sys.path.insert(0, os.path.join(_SCRIPT_DIR, "libs"))
from recon import parse_directive
from enrich import enrich_asset, yt_dlp_available
from scribe import get_transcript

OUT_DIR = os.path.join(_F01_DIR, "OUT")
IN_DIR = os.path.join(_F01_DIR, "IN")
CAMPAIGN_DIR = os.path.join(_FORGE_ROOT, "ARCHIVUM", "campaign")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _reference_clip_meta(reference_clip_path: str) -> dict:
    """Extrait les métadonnées du clip de référence fourni par la campagne."""
    if not os.path.exists(reference_clip_path):
        return {}
    try:
        data = load_json(reference_clip_path)
    except (json.JSONDecodeError, OSError):
        return {}
    url = data.get("url") or data.get("video_url")
    video_id = None
    if url:
        m = re.search(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})", url)
        video_id = m.group(1) if m else None
    return {
        "url": url,
        "video_id": video_id,
        "title": data.get("title"),
        "duration_sec": data.get("duration_sec") or data.get("duration"),
        "view_count": data.get("view_count"),
        "thumbnail": data.get("thumbnail"),
        "platform": data.get("platform", "youtube"),
        "metrics_extracted": data.get("metrics_extracted", {}),
    }


def _resolve_source_path(value: str, base_dir: str) -> str:
    if not value:
        return ""
    return value if os.path.isabs(value) else os.path.abspath(os.path.join(base_dir, value))


def cmd_meme_v2(args):
    """F01 MEME V2 : archive une source sociale fournie manuellement.
    Le texte est interne à PERTURABO ; la capture est l’asset destiné au pack."""
    source_path = args.meme_v2_source
    if not os.path.isabs(source_path):
        source_path = os.path.join(_FORGE_ROOT, source_path)
    data = load_json(source_path)
    source = data.get("source_post") or data
    screenshot = _resolve_source_path(source.get("screenshot_png"),
                                      os.path.dirname(source_path))
    if not source.get("text"):
        print("[F01:MEME_V2] source_post.text manquant")
        sys.exit(1)
    if not screenshot or not os.path.isfile(screenshot):
        print(f"[F01:MEME_V2] capture PNG introuvable: {screenshot or 'vide'}")
        sys.exit(1)
    campaign_id = data.get("campaign_id") or "manual_meme_v2"
    source_internal = dict(source)
    source_internal["screenshot_png"] = screenshot
    specimen = {
        "campaign_id": campaign_id,
        "mode": "meme_v2",
        "scanned_at": now_iso(),
        "source_post": source_internal,
        "assets": [{
            "asset_id": "source_tweet_capture",
            "type": "image",
            "path": screenshot,
            "url": source.get("url"),
            "source_permission": "operator_provided"
        }],
        "check_in_iw_custos": None,
        "iron_status": "manual_meme_v2",
        "vision_required": False,
    }
    save_json(os.path.join(OUT_DIR, "source_post.json"), source_internal)
    save_json(os.path.join(OUT_DIR, "source_specimen.json"), specimen)
    print(f"[F01:MEME_V2] source_post archivé : {os.path.join(OUT_DIR, 'source_post.json')}")
    print(f"[F01:MEME_V2] capture PNG : {screenshot}")
    print("[F01:MEME_V2] vision non requise : texte source fourni par l’opérateur")


def cmd_prepare(args):
    """Phase 1 — génère le prompt IRON + source_specimen.json pré-rempli."""
    directive_path = args.directive
    if not os.path.isabs(directive_path):
        directive_path = os.path.join(_FORGE_ROOT, directive_path)

    recon = parse_directive(directive_path)
    ref_path = args.reference_clip
    if not os.path.isabs(ref_path):
        ref_path = os.path.join(_FORGE_ROOT, ref_path)
    reference = _reference_clip_meta(ref_path)

    prompt = {
        "mission": "F01_SCOUT — Reconnaissance de la campagne (IRON sandbox). "
                   "Analyse les assets fournis par la campagne (strict-source, règle C1). "
                   "Extrais les métadonnées, calcule l'outlier_score du clip de référence, "
                   "pré-squelette le clip de référence. Écris OUT/source_specimen.json.",
        "campaign_id": recon["campaign_id"],
        "directive_path": directive_path,
        "reference_clip": reference,
        "assets": recon["assets"],
        "output_attendu": "OUT/source_specimen.json (structure dans F01_SCOUT/CODEBASE/TRACKING.md)",
        "heresies_interdites": [
            "Chercher des vidéos hors des assets de la campagne",
            "Extension du territoire de chasse en adjacence",
            "Modifier/couper/monter les vidéos sources",
        ],
    }
    save_json(os.path.join(IN_DIR, "scout_prompt.json"), prompt)

    if not os.path.exists(os.path.join(OUT_DIR, "source_specimen.json")):
        specimen = {
            "campaign_id": recon["campaign_id"],
            "scanned_at": now_iso(),
            "reference_clip": reference,
            "assets": recon["assets"],
            "check_in_iw_custos": None,
            "iron_status": "pending",
        }
        save_json(os.path.join(OUT_DIR, "source_specimen.json"), specimen)

    print(f"[F01] Prompt IRON : {os.path.join(IN_DIR, 'scout_prompt.json')}")
    print(f"[F01] {recon['assets_count']} assets extraits de directive.md")
    print("[F01] Copier le prompt dans Claude sandbox -> OUT/source_specimen.json, puis --finalize")


def cmd_auto(args):
    """Analyse automatique sans IRON : enrichissement local + transcription."""
    directive_path = args.directive
    if not os.path.isabs(directive_path):
        directive_path = os.path.join(_FORGE_ROOT, directive_path)

    recon = parse_directive(directive_path)
    ref_path = args.reference_clip
    if not os.path.isabs(ref_path):
        ref_path = os.path.join(_FORGE_ROOT, ref_path)
    reference = _reference_clip_meta(ref_path)

    ytdlp = yt_dlp_available()
    assets = []
    for asset in recon["assets"]:
        enriched = enrich_asset(asset, use_yt_dlp=ytdlp)
        if args.transcribe and enriched.get("type") in ("video_long", "stream"):
            t = get_transcript(asset["url"], os.path.join(CAMPAIGN_DIR, "transcripts"))
            enriched["transcript_available"] = t["status"] == "OK"
            enriched["transcript_path"] = t.get("path") if t["status"] == "OK" else None
        assets.append(enriched)

    specimen = {
        "campaign_id": recon["campaign_id"],
        "scanned_at": now_iso(),
        "reference_clip": reference,
        "assets": assets,
        "check_in_iw_custos": now_iso(),
        "iron_status": "auto",
        "auto_notes": {
            "yt_dlp_used": ytdlp,
            "transcripts_attempted": bool(args.transcribe),
        },
    }
    save_json(os.path.join(OUT_DIR, "source_specimen.json"), specimen)
    print(f"[F01] --auto : specimen écrit (yt-dlp: {ytdlp})")


def _validate_specimen(specimen: dict) -> list[str]:
    errors = []
    if not specimen.get("campaign_id"):
        errors.append("campaign_id manquant")
    if specimen.get("mode") == "meme_v2":
        source = specimen.get("source_post") or {}
        screenshot = source.get("screenshot_png")
        if not source.get("text"):
            errors.append("MEME V2 source_post.text manquant")
        if not screenshot or not os.path.isfile(screenshot):
            errors.append("MEME V2 source_post.screenshot_png introuvable")
        return errors
    if not specimen.get("assets"):
        errors.append("assets vide — strict-source violé ou directive.md vide")
    for a in specimen.get("assets", []):
        if not a.get("url", "").startswith(("http://", "https://")):
            errors.append(f"asset {a.get('asset_id')} : url invalide")
    return errors


def cmd_finalize(args):
    """Phase 3 — valide cohérence, génère scout_report.md, check-in IW_CUSTOS."""
    specimen_path = os.path.join(OUT_DIR, "source_specimen.json")
    if not os.path.exists(specimen_path):
        print("[F01] OUT/source_specimen.json absent — lancer --prepare puis IRON, ou --auto")
        sys.exit(1)

    specimen = load_json(specimen_path)
    errors = _validate_specimen(specimen)
    if errors:
        print("[F01] Specimen invalide :")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    ref = specimen.get("reference_clip", {})
    lines = [
        "# F01_SCOUT — Rapport de reconnaissance",
        "",
        f"- Campagne : {specimen.get('campaign_id', 'N/A')}",
        f"- Clip de référence : {ref.get('title', 'N/A')} — vues: {ref.get('view_count', 'N/A')}",
        f"- Assets inventoriés : {len(specimen.get('assets', []))}",
        "",
        "## Assets",
        "",
        "| ID | Type | Durée | Transcript | URL |",
        "|---|---|---|---|---|",
    ]
    for a in specimen.get("assets", []):
        lines.append(f"| {a.get('asset_id')} | {a.get('type')} | "
                     f"{a.get('duration_sec', '?')} | "
                     f"{'oui' if a.get('transcript_available') else 'non'} "
                     f"| {a.get('url')} |")

    report_path = os.path.join(OUT_DIR, "scout_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    specimen["check_in_iw_custos"] = now_iso()
    save_json(specimen_path, specimen)

    custos = os.path.join(_FORGE_ROOT, "IW_CUSTOS.py")
    if os.path.exists(custos):
        subprocess.run([sys.executable, custos, "--mode", "check-in",
                        "--frigate", "F01", "--output", specimen_path],
                       capture_output=True, text=True, timeout=30)
    print(f"[F01] Finalize : {report_path}")
    print("[F01] Check-in IW_CUSTOS — liber_clipping.json statut F01 = done")


def main():
    parser = argparse.ArgumentParser(description="F01_SCOUT — La Reconnaissance de Fer")
    parser.add_argument("--prepare", action="store_true", help="Phase 1 : prompt IRON")
    parser.add_argument("--auto", action="store_true",
                        help="Analyse automatique locale (sans IRON)")
    parser.add_argument("--finalize", action="store_true", help="Phase 3 : validation + check-in")
    parser.add_argument("--directive", default="ARCHIVUM/campaign/directive.md")
    parser.add_argument("--reference-clip", default="ARCHIVUM/campaign/reference_clip.json")
    parser.add_argument("--transcribe", action="store_true",
                        help="Tente la transcription des vidéos (--auto)")
    parser.add_argument("--meme-v2-source", default=None,
                        help="Source JSON manuelle MEME V2 : texte + capture PNG + provenance")
    args = parser.parse_args()

    if args.meme_v2_source:
        cmd_meme_v2(args)
    elif args.prepare:
        cmd_prepare(args)
    elif args.auto:
        cmd_auto(args)
    elif args.finalize:
        cmd_finalize(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
