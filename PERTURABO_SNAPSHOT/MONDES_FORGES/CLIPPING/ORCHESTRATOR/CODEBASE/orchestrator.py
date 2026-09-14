"""
orchestrator.py — L'Orchestrateur du Forge CLIPPING
====================================================

Frégate-conductrice. Ne forge rien elle-même — elle synchronise F01-F06 +
TYRANT + F00_CAPTEURS + ANGLESMITH à travers les 4 Portes, et tient le ledger
(liber_clipping.json + IW_CUSTOS.py).

Usage:
  # Démarrage d'un siège (campagne active)
  python orchestrator.py --start-siege --directive ARCHIVUM/campaign/directive.md \
      --reference-clip ARCHIVUM/campaign/reference_clip.json \
      --platform youtube --market us_young_english --n-angles 10

  # Après chaque porte :
  python orchestrator.py --gate N --decision valide|rejete [--notes "..."]

  # Reprise après une pause :
  python orchestrator.py --resume

  # État du siège :
  python orchestrator.py --status

  # Fermeture campagne :
  python orchestrator.py --close-siege --final-payout-summary "..."
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ORCH_DIR = os.path.dirname(_SCRIPT_DIR)
_FORGE_ROOT = os.path.dirname(_ORCH_DIR)

sys.path.insert(0, _SCRIPT_DIR)
sys.path.insert(0, os.path.join(_SCRIPT_DIR, "libs"))

from gates import ouvrir_porte, valider_porte, rejeter_porte, portes_to_dict, reset_portes
from libs.ledger_manager import LedgerManager
from libs.siege_initializer import SiegeInitializer
from libs.gate_validator import GateValidator
from libs.omnis_watch_distributor import OmnisWatchDistributor

FREGATES = {
    "TYRANT": os.path.join(_FORGE_ROOT, "TYRANT"),
    "CAPTEURS": os.path.join(_FORGE_ROOT, "F00_CAPTEURS"),
    "F01": os.path.join(_FORGE_ROOT, "F01_SCOUT"),
    "F02": os.path.join(_FORGE_ROOT, "F02_TYRANT_CAMP"),
    "F03": os.path.join(_FORGE_ROOT, "F03_SOURCE_HUNTER"),
    "F04": os.path.join(_FORGE_ROOT, "F04_COPYWRITER"),
    "F05": os.path.join(_FORGE_ROOT, "F05_PACKAGER"),
    "F06": os.path.join(_FORGE_ROOT, "F06_TRACKER"),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def banner(siege_id: str):
    print(f"\n{'' + ''*58 + ''}")
    print(f"  PERTURABO CLIPPING — SIÈGE {siege_id:<31}")
    print(f"{'' + ''*58 + ''}\n")


def cmd_start_siege(args):
    init = SiegeInitializer()
    result = init.validate(args.directive, args.reference_clip,
                           args.platform, args.market, args.n_angles)
    if not result["valid"]:
        print("[ORCH]  Inputs invalides :")
        for e in result["errors"]:
            print(f"  - {e}")
        sys.exit(1)

    lm = LedgerManager()
    siege_id = init.generate_siege_id()
    lm.initialize(siege_id, result["inputs"]["directive_path"],
                  result["inputs"]["reference_clip_path"],
                  result["inputs"]["platform_target"],
                  result["inputs"]["market_target"],
                  result["inputs"]["n_angles"])
    banner(siege_id)

    # Inputs du Warsmith → inputs des frégates
    inputs = result["inputs"]
    f01_in = os.path.join(FREGATES["F01"], "IN")
    os.makedirs(f01_in, exist_ok=True)
    with open(os.path.join(f01_in, "brief.json"), "w", encoding="utf-8") as f:
        json.dump({
            "siege_id": siege_id,
            "directive_path": inputs["directive_path"],
            "reference_clip_path": inputs["reference_clip_path"],
            "platform_target": inputs["platform_target"],
            "market_target": inputs["market_target"],
            "n_angles": inputs["n_angles"],
        }, f, indent=2, ensure_ascii=False)

    print(f"[ORCH] Ledger initialisé : {siege_id}")
    print("[ORCH] Commandé F00_CAPTEURS recommandée AVANT Porte 1 (optionnel) :")
    print("  cd F00_CAPTEURS/CODEBASE && python capteurs.py --scan "
          "--campaign F00_CAPTEURS/IN/campaign_to_observe.json")
    print("\n[ORCH]  F01_SCOUT doit être activée :")
    print("  cd F01_SCOUT/CODEBASE && python scout.py --prepare --directive ../ARCHIVUM/campaign/directive.md")
    print("  # L'IRON (Claude sandbox) analyse → OUT/source_specimen.json")
    print("  python scout.py --finalize")
    print("\n[ORCH] Puis F02_TYRANT_CAMP :")
    print("  cd F02_TYRANT_CAMP/CODEBASE && python tyrant_camp.py --prepare --specimen ../F01_SCOUT/OUT/source_specimen.json")
    print("  # L'IRON → OUT/campaign_verdict.json")
    print("  python tyrant_camp.py --finalize")
    print("\n[ORCH] Ensuite : python orchestrator.py --resume")
    lm.append_event("siege_started")


def cmd_resume(args):
    lm = LedgerManager()
    data = lm.load()
    siege_id = data.get("siege_id")
    if not siege_id:
        print("[ORCH]  Aucun siège en cours. Lance : orchestrator.py --start-siege ...")
        return

    banner(siege_id)
    print(f"[ORCH] Campagne : {data.get('campaign_id', 'N/A')} — "
          f"porte courante : {data.get('current_porte', 'init')} — "
          f"statut : {data.get('campaign_status')}")

    validator = GateValidator()
    # Vérifier quels artefacts sont déjà présents par porte
    for gate in ["1", "2", "3", "4"]:
        ok, missing = validator.validate_porte(gate, n_angles=data.get("inputs_warsmith", {}).get("n_angles"))
        status = "" if ok else f" manque: {', '.join(missing)}"
        print(f"  Porte {gate} : {status}")

    print("\n[ORCH] Porte suivante à traiter :", _porte_a_traiter(data, validator))
    print("[ORCH] Reprendre avec : orchestrator.py --gate <N> --decision valide|rejete")


def _porte_a_traiter(data: dict, validator: GateValidator) -> str:
    """Détermine la porte suivante selon les artefacts présents."""
    validated = data.get("portes_validated", [])
    for gate in ["1", "2", "3", "4"]:
        if gate not in validated:
            return gate
    return "closed"


def cmd_gate(args):
    lm = LedgerManager()
    data = lm.load()
    if data.get("campaign_status") != "active":
        print("[ORCH]  Pas de campagne active.")
        return

    gate_num = str(args.gate)
    decision = args.decision
    notes = args.notes

    if decision == "valide":
        validator = GateValidator()
        n_angles = data.get("inputs_warsmith", {}).get("n_angles")
        ok, missing = validator.validate_porte(gate_num, n_angles=n_angles)
        if not ok:
            print(f"[ORCH]  Porte {gate_num} : artefacts manquants — validation refusée :")
            for m in missing:
                print(f"  - {m}")
            return
        valider_porte(gate_num, notes)
        lm.add_porte_validated(gate_num, "valide", notes)

        if gate_num == "4":
            dist = OmnisWatchDistributor()
            try:
                index = dist.distribute(data["siege_id"], n_angles)
                lm.update(packs_expedies_count=len(index["packs"]))
                print("[ORCH]  Porte 4 validée — packs expédiés vers OMNIS_WATCH.")
                print("[ORCH] F06_TRACKER prend le relais : python tracker.py --post ...")
            except FileNotFoundError as e:
                print(f"[ORCH]  {e}")

        # Transférer les artefacts vers les frégates suivantes
        _transfer_artefacts(gate_num, data)

    elif decision == "rejete":
        rejeter_porte(gate_num, notes)
        lm.add_porte_validated(gate_num, "rejete", notes)
        print(f"[ORCH]  Porte {gate_num} rejetée. Notes : {notes}")
        print(f"[ORCH] La frégate concernée doit être relancée avec les notes du Warsmith.")

    lm.append_event(f"gate_{gate_num}_{decision}")


def _transfer_artefacts(gate_num: str, data: dict):
    """Copie les artefacts d'une frégate vers l'IN/ des frégates suivantes."""
    if gate_num == "1":
        _copy(os.path.join(FREGATES["F02"], "OUT", "campaign_verdict.json"),
              os.path.join(FREGATES["F03"], "IN", "verdict.json"))
    elif gate_num == "2":
        _copy(os.path.join(FREGATES["F02"], "OUT", "angles.json"),
              os.path.join(FREGATES["F03"], "IN", "angles.json"))
        _copy(os.path.join(FREGATES["F02"], "OUT", "angles.json"),
              os.path.join(FREGATES["F04"], "IN", "angles.json"))
    elif gate_num == "3":
        _copy(os.path.join(FREGATES["F03"], "OUT", "source_specimen.json"),
              os.path.join(FREGATES["F04"], "IN", "source_specimen.json"))
        _copy(os.path.join(FREGATES["F04"], "OUT", "text_payload.json"),
              os.path.join(FREGATES["F05"], "IN", "text_payload.json"))


def _copy(src: str, dest: str):
    if not os.path.exists(src):
        print(f"[ORCH]  Artefact introuvable (transféré plus tard) : {src}")
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    import shutil
    shutil.copy2(src, dest)
    print(f"[ORCH]  Transfert : {src} → {dest}")


def cmd_close_siege(args):
    lm = LedgerManager()
    data = lm.load()
    if data.get("campaign_status") != "active":
        print("[ORCH]  Pas de campagne active à fermer.")
        return

    data["campaign_status"] = "closed"
    data["current_porte"] = "closed"
    data["siege_closed_at"] = now_iso()
    data["last_event"] = "siege_closed"
    if args.final_payout_summary:
        data["final_payout_summary"] = args.final_payout_summary
    lm.save()
    lm.append_event("campaign_closed")

    print("[ORCH]  Campagne fermée.")
    print("[ORCH] F06_TRACKER agrège les learnings : python tracker.py --close-campaign")
    print("[ORCH] Le Warsmith peut lancer la campagne suivante (campaign/ est libéré).")


def cmd_status(args):
    lm = LedgerManager()
    data = lm.load()
    siege_id = data.get("siege_id")
    if not siege_id:
        print("[ORCH] Aucun siège en cours.")
        return
    banner(siege_id)
    print(f"  Campaign status : {data.get('campaign_status')}")
    print(f"  Porte courante  : {data.get('current_porte')}")
    print(f"  Portes validées : {data.get('portes_validated')}")
    print(f"  Packs expédiés  : {data.get('packs_expedies_count')}")
    print(f"  Packs postés    : {data.get('packs_posted_count')}")
    fs = data.get("fregates_status", {})
    for code in ["F01", "F02", "ANGLESMITH", "F03", "F04", "F05", "F06", "TYRANT", "CAPTEURS"]:
        print(f"  {code:<11}: {fs.get(code.lower(), 'pending')}")


def main():
    parser = argparse.ArgumentParser(description="ORCHESTRATOR — Monde Forge CLIPPING")
    parser.add_argument("--start-siege", action="store_true", help="Démarrer un siège")
    parser.add_argument("--directive", default="ARCHIVUM/campaign/directive.md")
    parser.add_argument("--reference-clip", default="ARCHIVUM/campaign/reference_clip.json")
    parser.add_argument("--platform", default="youtube", choices=["youtube", "tiktok", "instagram"])
    parser.add_argument("--market", default="us_young_english")
    parser.add_argument("--n-angles", type=int, default=10)
    parser.add_argument("--gate", choices=["1", "2", "3", "4"])
    parser.add_argument("--decision", choices=["valide", "rejete"])
    parser.add_argument("--notes", default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--close-siege", action="store_true")
    parser.add_argument("--final-payout-summary", default=None)
    args = parser.parse_args()

    if args.start_siege:
        cmd_start_siege(args)
    elif args.gate and args.decision:
        cmd_gate(args)
    elif args.resume:
        cmd_resume(args)
    elif args.status:
        cmd_status(args)
    elif args.close_siege:
        cmd_close_siege(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
