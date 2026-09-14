"""
IW_CUSTOS.py — Gardien de la Flotte PERTURABO
==============================================

Seul agent autorisé à modifier fleet_status dans liber_perturabo.json.
Équivalent de SR_CUSTOS.py dans SANCTORUM.

Usage:
  python IW_CUSTOS.py --mode check-out --frigate F01
  python IW_CUSTOS.py --mode check-in --frigate F01 --output F01_SENTINEL/OUT/transcript.json
  python IW_CUSTOS.py --mode validate --schema liber_perturabo.json
  python IW_CUSTOS.py --mode status
"""

import argparse
import json
import os
import hashlib
from datetime import datetime, timezone

# Paths anchored to this script's directory
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CMS_PATH = os.path.join(_SCRIPT_DIR, "liber_perturabo.json")
CAMPAIGN_LOG = os.path.join(_SCRIPT_DIR, "TRACKING", "IW_CAMPAIGN_LOG.md")
TRANSFER_LOG = os.path.join(_SCRIPT_DIR, "TRACKING", "IW_TRANSFER_LOG.md")

VALID_FRIGATES = ["F01", "F02", "F03", "F04", "F05", "F06", "S01", "S02", "S03", "S04", "TYRANT", "CAPTEURS"]

FLEET_STATUS_FLOW = [
    "pending_reconnaissance",
    "tyrant_report_ready",
    "specimen_captured",
    "skeleton_extracted",
    "script_forged",
    "thumbnail_forged",
    "niche_mapped",
    "identity_forged",
    "short_specimen_captured",
    "short_skeleton_extracted",
    "short_script_forged",
    "short_first_frame_forged",
    "artefact_ready",
    "complete",
]

FRIGATE_STATUS_KEY = {
    "F01": "f01_sentinel",
    "F02": "f02_breacher",
    "F03": "f03_forgeward",
    "F04": "f04_herald",
    "F05": "f05_grand_compass",
    "F06": "f06_identity_forge",
    "S01": "s01_sentinel",
    "S02": "s02_breacher",
    "S03": "s03_forgeward",
    "S04": "s04_herald",
    "TYRANT": "tyrant_report",
    "CAPTEURS": "capteurs",
}

FRIGATE_TRANSITIONS = {
    "TYRANT": "tyrant_report_ready",
    "F01": "specimen_captured",
    "F02": "skeleton_extracted",
    "F03": "script_forged",
    "F04": "thumbnail_forged",
    "F05": "niche_mapped",
    "F06": "identity_forged",
    "S01": "short_specimen_captured",
    "S02": "short_skeleton_extracted",
    "S03": "short_script_forged",
    "S04": "short_first_frame_forged",
}

PRECONDITIONS = {
    "TYRANT": [],
    "F01": ["tyrant_report_ready"],
    "F02": ["specimen_captured"],
    "F03": ["skeleton_extracted"],
    "F04": ["script_forged"],
    "F05": ["specimen_captured"],
    "F06": ["niche_mapped"],
    "S01": ["tyrant_report_ready"],
    "S02": ["short_specimen_captured"],
    "S03": ["short_skeleton_extracted"],
    "S04": ["short_script_forged"],
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_cms() -> dict:
    with open(CMS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_cms(data: dict):
    with open(CMS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def log_campaign(event: str):
    os.makedirs(os.path.join(_SCRIPT_DIR, "TRACKING"), exist_ok=True)
    ts = now_iso()
    entry = f"\n## [{ts}] {event}\n"
    with open(CAMPAIGN_LOG, "a", encoding="utf-8") as f:
        f.write(entry)
    print(f"[IW_CUSTOS] LOG: {event}")


def log_transfer(source: str, dest: str, md5: str, status: str):
    os.makedirs(os.path.join(_SCRIPT_DIR, "TRACKING"), exist_ok=True)
    ts = now_iso()
    entry = f"| {ts} | {source} | {dest} | {md5} | {status} |\n"
    header_needed = not os.path.exists(TRANSFER_LOG)
    with open(TRANSFER_LOG, "a", encoding="utf-8") as f:
        if header_needed:
            f.write("| TIMESTAMP | SOURCE | DEST | MD5 | STATUS |\n")
            f.write("|-----------|--------|------|-----|--------|\n")
        f.write(entry)


def cmd_check_out(frigate: str):
    if frigate not in VALID_FRIGATES:
        print(f"[IW_CUSTOS] ERREUR: Frégate inconnue '{frigate}'")
        return
    cms = load_cms()
    key = FRIGATE_STATUS_KEY[frigate]
    cms[key]["status"] = "processing"
    cms["iw_custos"]["last_validation"] = now_iso()
    save_cms(cms)
    log_campaign(f"{frigate} — check-out — status: processing")
    print(f"[IW_CUSTOS] {frigate} autorisée à lire ses entrées.")


def cmd_check_in(frigate: str, output_path: str):
    if frigate not in VALID_FRIGATES:
        print(f"[IW_CUSTOS] ERREUR: Frégate inconnue '{frigate}'")
        return
    if not os.path.exists(output_path):
        print(f"[IW_CUSTOS] ERREUR: Fichier de sortie introuvable: {output_path}")
        cms = load_cms()
        cms[FRIGATE_STATUS_KEY[frigate]]["status"] = "error"
        cms["iw_custos"]["errors"].append(
            {"ts": now_iso(), "frigate": frigate, "msg": f"Output not found: {output_path}"}
        )
        save_cms(cms)
        return

    file_md5 = md5_file(output_path)
    cms = load_cms()
    key = FRIGATE_STATUS_KEY[frigate]
    cms[key]["status"] = "done"
    cms[key]["output_path"] = output_path
    cms["iw_custos"]["last_validation"] = now_iso()
    cms["iw_custos"]["errors"] = [e for e in cms["iw_custos"]["errors"]
                                   if e.get("frigate") != frigate]
    _advance_fleet_status(cms, frigate)
    save_cms(cms)
    log_transfer(f"{frigate}/CODEBASE", f"{frigate}/OUT/{os.path.basename(output_path)}",
                 file_md5, "OK")
    log_campaign(f"{frigate} — check-in — output: {output_path} — md5: {file_md5} — status: done")
    print(f"[IW_CUSTOS] {frigate} validée. fleet_status: {cms['fleet_status']}")


def _advance_fleet_status(cms: dict, completed_frigate: str):
    if completed_frigate not in FRIGATE_TRANSITIONS:
        return
    current = cms.get("fleet_status", "pending_reconnaissance")
    try:
        current_idx = FLEET_STATUS_FLOW.index(current)
    except ValueError:
        current_idx = 0

    for req in PRECONDITIONS.get(completed_frigate, []):
        try:
            req_idx = FLEET_STATUS_FLOW.index(req)
        except ValueError:
            req_idx = 0
        if current_idx < req_idx:
            print(f"[IW_CUSTOS] AVERTISSEMENT: {completed_frigate} check-in"
                  f" mais '{req}' non atteint (actuel: '{current}'). fleet_status inchangé.")
            return

    cms["fleet_status"] = FRIGATE_TRANSITIONS[completed_frigate]


def cmd_validate(schema_path: str):
    required_keys = [
        "fleet_status", "siege_id", "mode", "warsmith_brief",
        "tyrant_report", "f01_sentinel", "f02_breacher", "f03_forgeward",
        "f04_herald", "f05_grand_compass", "capteurs",
        "iw_custos", "gate_decisions", "final_output"
    ]
    try:
        with open(schema_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        missing = [k for k in required_keys if k not in data]
        if missing:
            print(f"[IW_CUSTOS] SCHEMA INVALIDE — Clés manquantes: {missing}")
        else:
            print(f"[IW_CUSTOS] SCHEMA VALIDE — {schema_path}")
        log_campaign(f"Schema validation PASS — {schema_path}")
    except json.JSONDecodeError as e:
        print(f"[IW_CUSTOS] ERREUR JSON: {e}")


def cmd_status():
    cms = load_cms()
    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║ IW_CUSTOS — ÉTAT DE LA FLOTTE PERTURABO                 ║")
    print("╠══════════════════════════════════════════════════════════╣")
    print(f"║ fleet_status    : {cms['fleet_status']:<38}║")
    print(f"║ siege_id        : {str(cms.get('siege_id', 'null')):<38}║")
    print(f"║ mode            : {str(cms.get('mode', 'null')):<38}║")
    print(f"║ F01 SENTINEL    : {cms['f01_sentinel']['status']:<38}║")
    print(f"║ F02 BREACHER    : {cms['f02_breacher']['status']:<38}║")
    print(f"║ F03 FORGEWARD   : {cms['f03_forgeward']['status']:<38}║")
    print(f"║ F04 HERALD      : {cms['f04_herald']['status']:<38}║")
    print(f"║ F05 GRAND COMPASS:{cms['f05_grand_compass']['status']:<37}║")
    print(f"║ TYRANT          : {cms['tyrant_report']['status']:<38}║")
    print(f"║ CAPTEURS        : {cms['capteurs']['status']:<38}║")
    print(f"║ Last validation : {(cms['iw_custos']['last_validation'] or 'jamais'):<37}║")
    errors = cms['iw_custos']['errors']
    print(f"║ Erreurs         : {str(len(errors)):<38}║")
    print("╚══════════════════════════════════════════════════════════╝\n")


def main():
    parser = argparse.ArgumentParser(description="IW_CUSTOS — Gardien de la Flotte PERTURABO")
    parser.add_argument("--mode", required=True,
                        choices=["check-out", "check-in", "validate", "status"])
    parser.add_argument("--frigate", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--schema", default=CMS_PATH)
    args = parser.parse_args()

    if args.mode == "check-out":
        if not args.frigate:
            print("[IW_CUSTOS] --frigate requis pour check-out")
            return
        cmd_check_out(args.frigate)
    elif args.mode == "check-in":
        if not args.frigate or not args.output:
            print("[IW_CUSTOS] --frigate et --output requis pour check-in")
            return
        cmd_check_in(args.frigate, args.output)
    elif args.mode == "validate":
        cmd_validate(args.schema)
    elif args.mode == "status":
        cmd_status()


if __name__ == "__main__":
    main()
