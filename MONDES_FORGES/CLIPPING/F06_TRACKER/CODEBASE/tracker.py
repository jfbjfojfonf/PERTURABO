"""
tracker.py — F06_TRACKER : Le Traqueur de la Forteresse (forge CLIPPING)
=======================================================================

Frégate post-Porte 4. Active la submission_checklist des packs F05,
enregistre les saisies du Warsmith (vues 1h/24h, payout), boucle le
learnings.json et ferme la campagne.

F06 ne fait PAS appel à l'IRON ni au premium : pur mécanique de log +
calcul. L'opérateur poste ; F06 logge seulement (jamais d'auto-post).

Commandes:
  python tracker.py --post --angle A01 --account clip_main
  python tracker.py --submit --angle A01
  python tracker.py --views --angle A01 --1h 1200 --24h 8000
  python tracker.py --payout --angle A01 --amount 12.50
  python tracker.py --close-campaign

Hérésies gardées :
  - Auto-poster / auto-submit (l'opérateur poste ; F06 logge)
  - Invoquer l'IRON ou le premium
  - Pondération activée avant 50 packs cumulés
  - Campagne jamais fermée (campaign/ resterait ongoing)
"""

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_F06_DIR = os.path.dirname(_SCRIPT_DIR)
_FORGE_ROOT = os.path.dirname(_F06_DIR)

sys.path.insert(0, os.path.join(_SCRIPT_DIR, "libs"))
from readings_validator import ReadingsValidator
from learnings_aggregator import LearningsAggregator
from channel_performance_updater import ChannelPerformanceUpdater

OUT_DIR = os.path.join(_F06_DIR, "OUT")
ARCHIVUM_DIR = os.path.join(_FORGE_ROOT, "ARCHIVUM")
F05_OUT = os.path.join(_FORGE_ROOT, "F05_PACKAGER", "OUT")
LEARNINGS_PATH = os.path.join(ARCHIVUM_DIR, "learnings", "learnings.json")
CHANNELS_DIR = os.path.join(ARCHIVUM_DIR, "channels")
LIBER_PATH = os.path.join(_FORGE_ROOT, "liber_clipping.json")
SUBMISSION_LOG_PATH = os.path.join(OUT_DIR, "submission_log.json")

RULES_CANDIDATES = [
    os.path.join(_FORGE_ROOT, "CONTRACTS", "clipping_rules.md"),
    os.path.join(ARCHIVUM_DIR, "rules", "clipping_rules.md"),
]

LOW_PAYOUT_RE = re.compile(r"low[_-]?payout[^0-9]*([0-9]+(?:\.[0-9]+)?)")
LOW_VIEWS_RE = re.compile(r"low[_-]?views[^0-9]*([0-9]+)")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str, default=None):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: str, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ----------------------------------------------------------------------
# Résolution des entrées
# ----------------------------------------------------------------------
def campaign_id() -> str:
    index = load_json(os.path.join(F05_OUT, "packs_index.json"))
    if index and index.get("campaign_id"):
        return index["campaign_id"]
    packs = _pack_paths()
    if packs:
        pack = load_json(packs[0])
        if pack:
            return pack.get("identite", {}).get("campaign_id")
    return None


def _pack_paths() -> list[str]:
    return sorted(glob.glob(os.path.join(F05_OUT, "production_pack_*.json")))


def find_pack(angle_id: str) -> dict:
    path = os.path.join(F05_OUT, f"production_pack_{angle_id}.json")
    pack = load_json(path)
    if not pack:
        print(f"[F06] Pack introuvable: {path}")
        sys.exit(1)
    return pack


def load_log() -> dict:
    log = load_json(SUBMISSION_LOG_PATH)
    if log is None:
        log = {
            "campaign_id": campaign_id(),
            "campaign_status": "ongoing",
            "packs": [],
            "cumulative": {
                "packs_count": 0,
                "eligible_for_learning_weight": False,
                "aggregate_cpm": None,
            },
            "log_event": [],
        }
        save_json(SUBMISSION_LOG_PATH, log)
    return log


def thresholds() -> dict:
    text = ""
    for path in RULES_CANDIDATES:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    text += "\n" + f.read()
            except OSError:
                pass
    low_payout = LOW_PAYOUT_RE.search(text)
    low_views = LOW_VIEWS_RE.search(text)
    return {
        "low_payout": float(low_payout.group(1)) if low_payout else 0.0,
        "low_views": int(low_views.group(1)) if low_views else 0,
        "declared": bool(low_payout or low_views),
    }


def _log_event(log: dict, event: str, angle_id: str = None):
    entry = {"at": now_iso(), "event": event}
    if angle_id:
        entry["angle_id"] = angle_id
    log.setdefault("log_event", []).append(entry)


def _pack_entry(log: dict, angle_id: str) -> dict:
    for pack in log["packs"]:
        if pack.get("angle_id") == angle_id:
            return pack
    entry = {
        "angle_id": angle_id,
        "platform": None,
        "market": None,
        "posted_at": None,
        "posted_by_account": None,
        "submitted_whop_at": None,
        "submission_within_1h": None,
        "views_1h": None,
        "views_24h": None,
        "payout_expected": None,
        "payout_observed": None,
        "payout_flag": None,
        "suggested_flags": [],
        "items_closed": [],
        "items_pending": [],
    }
    log["packs"].append(entry)
    return entry


def _update_items(entry: dict, pack: dict, done_ids: list[str]):
    items = pack.get("submission_checklist", {}).get("items", []) or []
    entry["items_closed"] = sorted(done_ids)
    entry["items_pending"] = sorted(
        i.get("id") for i in items if i.get("id") not in done_ids)


def _mark_flag(entry: dict, flag: str):
    if flag not in entry["suggested_flags"]:
        entry["suggested_flags"].append(flag)


# ----------------------------------------------------------------------
# Commandes
# ----------------------------------------------------------------------
def cmd_post(args):
    pack = find_pack(args.angle)
    validator = ReadingsValidator()
    issues = validator.validate_post(args, pack, load_log())
    if issues:
        print("[F06] Saisie invalide :")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)

    log = load_log()
    if log["campaign_status"] != "ongoing":
        print(f"[F06] Campagne {log['campaign_status']} — pas de nouveau post")
        sys.exit(1)

    entry = _pack_entry(log, args.angle)
    identite = pack.get("identite", {})
    angle_block = pack.get("angle", {})
    entry["platform"] = pack.get("cibles", {}).get("target_platform")
    entry["market"] = pack.get("cibles", {}).get("target_market")
    entry["angle_family"] = angle_block.get("angle_family")
    entry["emotion_mode"] = angle_block.get("emotion_mode")
    entry["engagement_type"] = angle_block.get("engagement_type")
    entry["reframe_dim"] = angle_block.get("reframe_dim")
    entry["posted_at"] = now_iso()
    entry["posted_by_account"] = args.account
    _update_items(entry, pack, done_ids=["post_on_platform"])
    _log_event(log, "pack_posted", args.angle)

    updater = ChannelPerformanceUpdater(CHANNELS_DIR)
    updater.record_pack(args.account, identite.get("campaign_id"), args.angle,
                        entry["posted_at"])

    save_json(SUBMISSION_LOG_PATH, log)
    print(f"[F06] Pack posté : {args.angle} sur {entry['platform']} "
          f"(compte {args.account}) — checklist activée")


def cmd_submit(args):
    log = load_log()
    entry = _pack_entry(log, args.angle)
    if not entry.get("posted_at"):
        print(f"[F06] {args.angle} pas encore posté — --post d'abord")
        sys.exit(1)

    pack = find_pack(args.angle)
    deadline_min = 60
    for item in pack.get("submission_checklist", {}).get("items", []) or []:
        if item.get("id") == "submit_whop_under_1h" and item.get("deadline_min"):
            deadline_min = item["deadline_min"]

    posted = datetime.fromisoformat(entry["posted_at"].replace("Z", "+00:00"))
    submitted = datetime.now(timezone.utc)
    entry["submitted_whop_at"] = submitted.strftime("%Y-%m-%dT%H:%M:%SZ")
    within = (submitted - posted).total_seconds() <= deadline_min * 60
    entry["submission_within_1h"] = bool(within)
    if not within:
        _mark_flag(entry, "submission_late")

    closed = set(entry.get("items_closed", []))
    closed.add("submit_whop_under_1h")
    _update_items(entry, pack, done_ids=sorted(closed))
    _log_event(log, "submission_done", args.angle)
    save_json(SUBMISSION_LOG_PATH, log)
    print(f"[F06] Soumission Whop : {args.angle} "
          f"{'dans les ' + str(deadline_min) + ' min' if within else 'EN RETARD'}")


def cmd_views(args):
    log = load_log()
    entry = _pack_entry(log, args.angle)
    if not entry.get("posted_at"):
        print(f"[F06] {args.angle} pas encore posté — --post d'abord")
        sys.exit(1)

    validator = ReadingsValidator()
    issues = validator.validate_views(args, entry)
    if issues:
        print("[F06] Saisie invalide :")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)

    th = thresholds()
    pack = find_pack(args.angle)
    entry["views_1h"] = int(args.v1h)
    entry["views_24h"] = int(args.v24h)
    if th["declared"] and entry["views_24h"] < th["low_views"]:
        _mark_flag(entry, "low_views")

    closed = set(entry.get("items_closed", []))
    closed.update(["view_check_1h", "view_check_24h"])
    _update_items(entry, pack, done_ids=sorted(closed))
    _log_event(log, "view_check", args.angle)
    save_json(SUBMISSION_LOG_PATH, log)

    updater = ChannelPerformanceUpdater(CHANNELS_DIR)
    updater.update_views(entry.get("posted_by_account"), args.angle,
                         entry["views_1h"], entry["views_24h"])
    print(f"[F06] Vues enregistrées : {args.angle} — 1h: {args.v1h}, 24h: {args.v24h}")


def cmd_payout(args):
    log = load_log()
    entry = _pack_entry(log, args.angle)
    if not entry.get("posted_at"):
        print(f"[F06] {args.angle} pas encore posté — --post d'abord")
        sys.exit(1)

    validator = ReadingsValidator()
    issues = validator.validate_payout(args, entry)
    if issues:
        print("[F06] Saisie invalide :")
        for i in issues:
            print(f"  - {i}")
        sys.exit(1)

    th = thresholds()
    pack = find_pack(args.angle)
    entry["payout_observed"] = float(args.amount)
    entry["payout_flag"] = "low" if entry["payout_observed"] < th["low_payout"] else "ok"
    if entry["payout_flag"] == "low":
        _mark_flag(entry, "low_payout")

    closed = set(entry.get("items_closed", []))
    closed.add("payout_flag_low")
    _update_items(entry, pack, done_ids=sorted(closed))
    _log_event(log, "payout_recorded", args.angle)
    save_json(SUBMISSION_LOG_PATH, log)

    updater = ChannelPerformanceUpdater(CHANNELS_DIR)
    updater.update_payout(entry.get("posted_by_account"), args.angle,
                          entry["payout_observed"])
    print(f"[F06] Payout enregistré : {args.angle} — ${args.amount} "
          f"(flag: {entry['payout_flag']})")


def cmd_close_campaign(args):
    log = load_log()
    if log["campaign_status"] == "closed":
        print(f"[F06] Campagne déjà fermée : {log.get('campaign_id')}")
        sys.exit(1)
    if not log["packs"]:
        print("[F06] Aucun pack enregistré — rien à fermer")
        sys.exit(1)

    aggregator = LearningsAggregator(LEARNINGS_PATH)
    learnings = aggregator.aggregate(log)
    save_json(LEARNINGS_PATH, learnings)

    eligible = learnings.get("eligible_for_weighting", False)
    log["cumulative"]["packs_count"] = learnings.get("cumulative_packs_executed", 0)
    log["cumulative"]["eligible_for_learning_weight"] = eligible
    totals = [p.get("payout_observed") or 0 for p in log["packs"]]
    total_views = sum(p.get("views_24h") or 0 for p in log["packs"])
    log["cumulative"]["aggregate_cpm"] = (
        round(sum(totals) / (total_views / 1000.0), 2) if total_views > 0 else None)
    log["campaign_status"] = "closed"
    _log_event(log, "campaign_closed")
    save_json(SUBMISSION_LOG_PATH, log)

    summary_path = _write_campaign_summary(log, learnings)

    custos = os.path.join(_FORGE_ROOT, "IW_CUSTOS.py")
    if os.path.exists(custos):
        subprocess.run([sys.executable, custos, "--mode", "check-in",
                        "--frigate", "F06", "--output", summary_path],
                       capture_output=True, text=True, timeout=30)
        subprocess.run([sys.executable, custos, "--mode", "close-campaign"],
                       capture_output=True, text=True, timeout=30)
    print(f"[F06] Campagne fermée — {summary_path}")
    print(f"[F06] Learnings mis à jour : cumulative {learnings.get('cumulative_packs_executed')} "
          f"packs — pondération {'ACTIVÉE (>= 50)' if eligible else 'neutre (< 50)'}")
    print("[F06] Réarme possible : archiver/effacer ARCHIVUM/campaign/ puis nouveau siège")


def _write_campaign_summary(log: dict, learnings: dict) -> str:
    lines = [
        "# F06_TRACKER — Synthèse de campagne",
        "",
        f"- Campagne : {log.get('campaign_id') or 'N/A'}",
        f"- Statut : closed",
        f"- Packs postés : {len(log['packs'])}",
        f"- Packs cumulés (toutes campagnes) : {learnings.get('cumulative_packs_executed')}",
        f"- Pondération learnings : "
        f"{'ACTIVÉE' if learnings.get('eligible_for_weighting') else 'neutre (< 50 packs)'}",
        "",
        "| Angle | Plateforme | Compte | Soumis <1h | Vues 1h | Vues 24h | Payout | Flags |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for p in log["packs"]:
        flags = ", ".join(p.get("suggested_flags", []) or []) or "—"
        submit = "oui" if p.get("submission_within_1h") else "non"
        lines.append(
            f"| {p.get('angle_id')} | {p.get('platform')} | {p.get('posted_by_account')} "
            f"| {submit} | {p.get('views_1h') or '—'} | {p.get('views_24h') or '—'} "
            f"| {p.get('payout_observed') or '—'} | {flags} |")
    lines.append("")
    lines.append("*Fer au-dedans, Fer au-dehors. Le siège est fini quand le tracker a fermé le ledger.*")
    path = os.path.join(OUT_DIR, "campaign_summary.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def main():
    parser = argparse.ArgumentParser(description="F06_TRACKER — Le Traqueur de la Forteresse")
    parser.add_argument("--post", action="store_true", help="Marque le pack posté (checklist active)")
    parser.add_argument("--submit", action="store_true", help="Marque la soumission Whop")
    parser.add_argument("--views", action="store_true", help="Enregistre les vues 1h + 24h")
    parser.add_argument("--payout", action="store_true", help="Enregistre le payout observé")
    parser.add_argument("--close-campaign", action="store_true",
                        help="Ferme la campagne + agrège learnings + summary")
    parser.add_argument("--angle", default=None, help="angle_id (ex: A01)")
    parser.add_argument("--account", default=None, help="slug du compte qui a posté")
    parser.add_argument("--1h", dest="v1h", default=None, help="Vues à 1h")
    parser.add_argument("--24h", dest="v24h", default=None, help="Vues à 24h")
    parser.add_argument("--amount", default=None, help="Payout observé (float)")
    args = parser.parse_args()

    if args.post:
        if not args.angle or not args.account:
            print("[F06] --angle et --account requis pour --post"); sys.exit(1)
        cmd_post(args)
    elif args.submit:
        if not args.angle:
            print("[F06] --angle requis pour --submit"); sys.exit(1)
        cmd_submit(args)
    elif args.views:
        if not args.angle or args.v1h is None or args.v24h is None:
            print("[F06] --angle, --1h et --24h requis pour --views"); sys.exit(1)
        cmd_views(args)
    elif args.payout:
        if not args.angle or args.amount is None:
            print("[F06] --angle et --amount requis pour --payout"); sys.exit(1)
        cmd_payout(args)
    elif args.close_campaign:
        cmd_close_campaign(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
