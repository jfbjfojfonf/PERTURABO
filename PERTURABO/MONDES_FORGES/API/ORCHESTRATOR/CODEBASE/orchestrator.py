"""
ORCHESTRATOR — Monde-Forge API
================================
Le nerf central. Enchaîne toutes les frégates en une seule commande.

Usage:
  python orchestrator.py --enclenche              → siège complet auto (TYRANT identifie la cible)
  python orchestrator.py --enclenche --hint "LinkedIn scraper"  → hint optionnel
  python orchestrator.py --resume                 → reprendre un siège interrompu
  python orchestrator.py --status                 → état du siège en cours
  python orchestrator.py --rapport                → rapport de survie (post-deploy)
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

MONDE_ROOT = Path(__file__).parent.parent
CORE_ROOT = MONDE_ROOT.parent.parent / "CORE"
sys.path.insert(0, str(CORE_ROOT))

LIBER = MONDE_ROOT / "liber_api.json"
ARCHIVUM = MONDE_ROOT / "ARCHIVUM"
LEDGERS = ARCHIVUM / "ledgers"

# Chemins frégates
FREGATES = {
    "TYRANT":  MONDE_ROOT / "TYRANT" / "CODEBASE" / "tyrant.py",
    "F01":     MONDE_ROOT / "fregates" / "F01_SENTINEL" / "CODEBASE" / "sentinel.py",
    "F02":     MONDE_ROOT / "fregates" / "F02_BREACHER" / "CODEBASE" / "breacher.py",
    "F03":     MONDE_ROOT / "fregates" / "F03_FORGEWARD" / "CODEBASE" / "forgeward.py",
    "F04":     MONDE_ROOT / "fregates" / "F04_HERALD" / "CODEBASE" / "herald.py",
    "F05":     MONDE_ROOT / "fregates" / "F05_GRAND_COMPASS" / "CODEBASE" / "grand_compass.py",
    "F06":     MONDE_ROOT / "fregates" / "F06_CAPTEURS" / "CODEBASE" / "capteurs.py",
}

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║          P E R T U R A B O  —  M O N D E - F O R G E  A P I ║
║                    LE MAÎTRE DU SIÈGE                        ║
╚══════════════════════════════════════════════════════════════╝"""


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _load_liber() -> dict:
    with open(LIBER) as f:
        return json.load(f)


def _save_liber(liber: dict):
    liber["siege_timestamps"] = liber.get("siege_timestamps", {})
    with open(LIBER, "w") as f:
        json.dump(liber, f, indent=2, ensure_ascii=False)


def _run_frigate(frigate_key: str, *args) -> int:
    """Lance une frégate et retourne le code de retour."""
    script = FREGATES.get(frigate_key)
    if not script or not script.exists():
        print(f"[ORCH] ERREUR : {frigate_key} introuvable à {script}")
        return 1
    cmd = [sys.executable, str(script)] + list(args)
    print(f"\n[ORCH] → {frigate_key} {' '.join(args)}")
    result = subprocess.run(cmd, cwd=script.parent)
    return result.returncode


def _gate(gate_num: int, label: str, display_fn=None) -> bool:
    """
    Présente une porte au Warsmith et attend sa décision.
    Retourne True si validé, False si rejeté.
    """
    print(f"\n{'═'*62}")
    print(f"  GATE {gate_num} — {label}")
    print(f"{'═'*62}")

    if display_fn:
        display_fn()

    print(f"\n  Warsmith — décision requise :")
    print(f"  [O] Valider et continuer")
    print(f"  [N] Rejeter et arrêter")
    print(f"{'─'*62}")

    while True:
        try:
            choice = input("  Décision [O/N] : ").strip().upper()
        except (EOFError, KeyboardInterrupt):
            print("\n[ORCH] Siège interrompu.")
            return False

        if choice == "O":
            liber = _load_liber()
            liber["gate_decisions"][f"gate_{gate_num}"] = {
                "validated": True,
                "timestamp": now_iso(),
                "label": label
            }
            _save_liber(liber)
            print(f"  Gate {gate_num} validée.")
            return True
        elif choice == "N":
            liber = _load_liber()
            liber["gate_decisions"][f"gate_{gate_num}"] = {
                "validated": False,
                "timestamp": now_iso(),
                "label": label
            }
            _save_liber(liber)
            print(f"  Gate {gate_num} rejetée — siège arrêté.")
            return False
        else:
            print("  Réponse invalide. Tape O ou N.")


def _display_tyrant():
    """Affiche le rapport TYRANT pour Gate 1."""
    liber = _load_liber()
    report = liber.get("tyrant_report", {})
    if not report:
        print("  Rapport TYRANT non disponible.")
        return
    print(f"  Cible        : {report.get('cible_nom', '?')}")
    print(f"  Score        : {report.get('score_global', '?')}/100")
    print(f"  Faille       : {report.get('faille_principale', '?')}")
    print(f"  Latence      : {report.get('latence_ms', '?')}ms")
    print(f"  Prix leader  : {report.get('prix_leader', '?')}")
    print(f"  Wrappers GH  : {report.get('wrappers_github', '?')}")


def _display_breacher():
    """Affiche le résumé BREACHER pour Gate 2."""
    liber = _load_liber()
    f02 = liber.get("f02", {})
    angles = f02.get("angles_attaque", [])
    print(f"  Cible confirmée : {f02.get('cible', '?')}")
    print(f"  Score           : {f02.get('score', '?')}/100")
    print(f"  Angles d'attaque : {len(angles)}")
    for a in angles[:5]:
        print(f"    [{a.get('id','?'):02d}] {a.get('type','?')} — {a.get('description','?')[:50]}")
    if len(angles) > 5:
        print(f"    ... +{len(angles)-5} autres")


def _display_forgeward():
    """Affiche le récap FORGEWARD pour Gate 3."""
    warriors_path = MONDE_ROOT / "fregates" / "F03_FORGEWARD" / "OUT" / "warriors.json"
    if not warriors_path.exists():
        print("  warriors.json non disponible.")
        return
    with open(warriors_path) as f:
        data = json.load(f)
    warriors = [w for w in data.get("warriors", []) if w.get("status") != "error"]
    print(f"  Iron Warriors forgés : {len(warriors)}/20")
    for w in warriors[:5]:
        print(f"    [{w.get('warrior_id',0):02d}] {w.get('api_title','?')[:45]} — {w.get('pricing_tier','?')}")
    if len(warriors) > 5:
        print(f"    ... +{len(warriors)-5} autres")


def _display_herald():
    """Affiche le récap HERALD pour Gate 4."""
    listings_path = MONDE_ROOT / "fregates" / "F04_HERALD" / "OUT" / "listings_output.json"
    if not listings_path.exists():
        print("  listings_output.json non disponible.")
        return
    with open(listings_path) as f:
        data = json.load(f)
    listings = [l for l in data.get("listings", []) if l.get("status") != "error"]
    print(f"  Listings RapidAPI prêts : {len(listings)}/20")
    for l in listings[:5]:
        print(f"    [{l.get('warrior_id',0):02d}] {l.get('rapidapi_title','?')[:50]}")
        print(f"         Prix : {l.get('pricing_pro','?')}")
    if len(listings) > 5:
        print(f"    ... +{len(listings)-5} autres")


def cmd_enclenche(hint: str = None):
    """Siège complet : TYRANT → F01 → F02 → Gate → F03 → F04 → Gate → F05 → F06."""
    print(BANNER)
    t_start = time.time()
    now = now_iso()

    # Reset liber
    ret = _run_frigate("TYRANT") or 0  # dummy pour reset via IW_CUSTOS
    liber = _load_liber()
    # Générer un siege_id
    siege_id = f"API-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    liber["siege_id"] = siege_id
    liber["fleet_status"] = "sentinel_running"
    liber["warsmith_brief"]["mode"] = "enclenche"
    liber["warsmith_brief"]["categorie_hint"] = hint
    liber["siege_timestamps"]["start"] = now
    _save_liber(liber)

    print(f"\n[ORCH] Siège lancé : {siege_id}")
    if hint:
        print(f"[ORCH] Hint Warsmith : {hint}")
    print(f"[ORCH] Temps cible : < 60 minutes\n")

    # ─── PHASE RENSEIGNEMENT ────────────────────────────────────────
    print("\n[ORCH] ═══ PHASE 1 : RENSEIGNEMENT ═══")

    # F01 SENTINEL — scan multi-source
    for step in ["--prepare", "--iron", "--finalize"]:
        rc = _run_frigate("F01", step)
        if rc != 0:
            print(f"[ORCH] ERREUR F01 {step} (code {rc}) — siège interrompu")
            return

    # TYRANT — analyse et identification cible
    print("\n[ORCH] ═══ TYRANT — Identification de la forteresse ═══")
    for step in ["--prepare", "--iron", "--finalize"]:
        rc = _run_frigate("TYRANT", step)
        if rc != 0:
            print(f"[ORCH] ERREUR TYRANT {step} (code {rc}) — siège interrompu")
            return

    # ─── GATE 1 — Warsmith valide la cible ──────────────────────────
    ok = _gate(1, "Validation de la cible", _display_tyrant)
    if not ok:
        return

    # ─── PHASE ANALYSE ──────────────────────────────────────────────
    print("\n[ORCH] ═══ PHASE 2 : ANALYSE — 20 ANGLES D'ATTAQUE ═══")

    # F02 BREACHER — scoring + angles d'attaque
    for step in ["--prepare", "--iron", "--finalize"]:
        rc = _run_frigate("F02", step)
        if rc != 0:
            print(f"[ORCH] ERREUR F02 {step} (code {rc}) — siège interrompu")
            return

    # ─── GATE 2 — Warsmith valide les 20 angles ─────────────────────
    ok = _gate(2, "Validation des 20 angles d'attaque", _display_breacher)
    if not ok:
        return

    # ─── PHASE FORGE ────────────────────────────────────────────────
    print("\n[ORCH] ═══ PHASE 3 : FORGE — 20 IRON WARRIORS ═══")

    # F03 FORGEWARD — 20 codes FastAPI en parallèle
    for step in ["--prepare", "--iron", "--finalize"]:
        rc = _run_frigate("F03", step)
        if rc != 0:
            print(f"[ORCH] ERREUR F03 {step} (code {rc}) — siège interrompu")
            return

    # ─── GATE 3 — Warsmith valide les warriors forgés ───────────────
    ok = _gate(3, "Validation des Iron Warriors forgés", _display_forgeward)
    if not ok:
        return

    # F04 HERALD — listings RapidAPI + README
    print("\n[ORCH] ═══ PHASE 4 : HERALD — LISTINGS RAPIDAPI ═══")
    for step in ["--prepare", "--iron", "--finalize"]:
        rc = _run_frigate("F04", step)
        if rc != 0:
            print(f"[ORCH] ERREUR F04 {step} (code {rc}) — siège interrompu")
            return

    # ─── GATE 4 — Warsmith valide les listings ──────────────────────
    ok = _gate(4, "Validation des listings RapidAPI", _display_herald)
    if not ok:
        return

    # ─── PHASE DEPLOY ───────────────────────────────────────────────
    print("\n[ORCH] ═══ PHASE 5 : DEPLOY — IRON WARRIORS EN LIGNE ═══")

    # F05 GRAND COMPASS — deploy GitHub + URLs Railway
    for step in ["--prepare", "--iron", "--finalize"]:
        rc = _run_frigate("F05", step)
        if rc != 0:
            print(f"[ORCH] ERREUR F05 {step} (code {rc}) — siège interrompu")
            return

    # F06 CAPTEURS — initialiser le monitoring
    rc = _run_frigate("F06", "--init", "--siege-id", siege_id)
    if rc != 0:
        print(f"[ORCH] AVERTISSEMENT F06 --init (code {rc}) — monitoring non initialisé")

    # ─── SIÈGE TERMINÉ ──────────────────────────────────────────────
    t_end = time.time()
    elapsed = int(t_end - t_start)
    mins, secs = divmod(elapsed, 60)

    liber = _load_liber()
    liber["fleet_status"] = "deployed"
    liber["siege_timestamps"]["end"] = now_iso()
    liber["siege_timestamps"]["duration_seconds"] = elapsed
    _save_liber(liber)

    print(f"\n{'╔' + '═'*62 + '╗'}")
    print(f"║  SIÈGE TERMINÉ — {siege_id:<45}║")
    print(f"║  Durée : {mins}m{secs:02d}s{' '*(51-len(f'{mins}m{secs:02d}s'))}║")
    print(f"╠{'═'*62}╣")
    print(f"║  Prochaines actions Warsmith :                               ║")
    print(f"║  1. Clique les liens Railway pour finaliser le deploy        ║")
    print(f"║  2. Publie chaque API sur RapidAPI (copie listing_rapidapi)  ║")
    print(f"║  3. Remplis rapidapi_slug dans le ledger F06                 ║")
    print(f"║  4. Lance quotidiennement : python capteurs.py --scan        ║")
    print(f"╚{'═'*62}╝")

    # Afficher les URLs de deploy
    deploy_path = MONDE_ROOT / "fregates" / "F05_GRAND_COMPASS" / "OUT" / "deploy_results.json"
    if deploy_path.exists():
        with open(deploy_path) as f:
            deploy_data = json.load(f)
        results = [r for r in deploy_data.get("results", []) if r.get("status") == "deployed"]
        if results:
            print(f"\n  URLs Railway ({len(results)} warriors) :")
            for r in results[:10]:
                print(f"  [{r['warrior_id']:02d}] {r.get('railway_deploy_url','?')}")
            if len(results) > 10:
                print(f"  ... +{len(results)-10} autres dans deploy_results.json")


def cmd_resume():
    """Reprend un siège interrompu selon le fleet_status du liber."""
    liber = _load_liber()
    status = liber.get("fleet_status", "idle")
    siege_id = liber.get("siege_id", "?")

    print(f"\n[ORCH] Reprise du siège {siege_id} — statut : {status}")

    status_to_phase = {
        "sentinel_running": ("F01", ["--prepare", "--iron", "--finalize"]),
        "intel_captured": ("TYRANT", ["--prepare", "--iron", "--finalize"]),
        "tyrant_report_ready": None,  # Gate 1 en attente
        "target_scored": ("F02", ["--prepare", "--iron", "--finalize"]),
        "ironwarriors_forged": ("F03", ["--prepare", "--iron", "--finalize"]),
        "listings_ready": ("F04", ["--prepare", "--iron", "--finalize"]),
        "market_mapped": ("F05", ["--prepare", "--iron", "--finalize"]),
    }

    if status == "idle":
        print("[ORCH] Aucun siège en cours. Lance --enclenche.")
        return

    if status == "deployed":
        print("[ORCH] Siège déjà déployé. Lance --rapport pour le monitoring.")
        return

    if status in status_to_phase and status_to_phase[status]:
        frigate, steps = status_to_phase[status]
        for step in steps:
            rc = _run_frigate(frigate, step)
            if rc != 0:
                print(f"[ORCH] ERREUR {frigate} {step}")
                return
    else:
        print(f"[ORCH] Statut '{status}' — reprise manuelle requise.")
        print(f"  Consulte le liber_api.json pour voir où le siège s'est arrêté.")


def cmd_status():
    """Affiche l'état complet du siège."""
    liber = _load_liber()
    siege_id = liber.get("siege_id", "aucun")
    status = liber.get("fleet_status", "idle")
    timestamps = liber.get("siege_timestamps", {})

    print(f"\n{'╔' + '═'*56 + '╗'}")
    print(f"║  PERTURABO — ÉTAT SIÈGE{' '*32}║")
    print(f"{'╠' + '═'*56 + '╣'}")
    print(f"║  Siege ID  : {siege_id:<43}║")
    print(f"║  Statut    : {status:<43}║")

    tyrant = liber.get("tyrant_report", {}) or {}
    f02 = liber.get("f02", {}) or {}
    f03 = liber.get("f03", {}) or {}
    f05 = liber.get("f05", {}) or {}
    gates = liber.get("gate_decisions", {}) or {}

    print(f"║  TYRANT    : {'cible=' + str(tyrant.get('cible_nom','?')):<43}║")
    print(f"║  F01 SENT. : {str(liber.get('f01',{}).get('status','idle')):<43}║")
    print(f"║  F02 BRCH. : {'score=' + str(f02.get('score','?')):<43}║")
    print(f"║  F03 FORGE : {str(f03.get('ironwarriors_count',0)) + ' warriors':<43}║")
    print(f"║  F04 HERALD: {str(liber.get('f04',{}).get('status','idle')):<43}║")
    print(f"║  F05 COMP. : {str(len(f05.get('deployed_urls',[]))) + ' deployed':<43}║")
    print(f"║  F06 CAPT. : {str(liber.get('f06',{}).get('status','idle')):<43}║")
    print(f"{'╠' + '═'*56 + '╣'}")

    for i in range(1, 5):
        g = gates.get(f"gate_{i}", {})
        ok = g.get("validated")
        symbol = "✓ validée" if ok else "✗ rejetée" if ok is False else "⏳ en attente"
        print(f"║  Gate {i}    : {symbol:<43}║")

    if timestamps.get("start"):
        print(f"{'╠' + '═'*56 + '╣'}")
        print(f"║  Début     : {timestamps['start'][:19]:<43}║")
        if timestamps.get("duration_seconds"):
            d = int(timestamps["duration_seconds"])
            m, s = divmod(d, 60)
            print(f"║  Durée     : {f'{m}m{s:02d}s':<43}║")
    print(f"{'╚' + '═'*56 + '╝'}")


def cmd_rapport(siege_id: str = None):
    """Lance le rapport de survie F06 CAPTEURS."""
    liber = _load_liber()
    sid = siege_id or liber.get("siege_id", "API-001")
    rc = _run_frigate("F06", "--report", "--siege-id", sid)
    if rc != 0:
        print(f"[ORCH] ERREUR F06 --report")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PERTURABO — Orchestrateur Monde-Forge API")
    parser.add_argument("--enclenche", action="store_true", help="Lancer un siège complet")
    parser.add_argument("--hint", default=None, help="Hint optionnel pour TYRANT (ex: 'LinkedIn scraper')")
    parser.add_argument("--resume", action="store_true", help="Reprendre un siège interrompu")
    parser.add_argument("--status", action="store_true", help="Afficher l'état du siège")
    parser.add_argument("--rapport", action="store_true", help="Rapport de survie post-deploy")
    parser.add_argument("--siege-id", default=None, help="ID du siège pour --rapport")
    args = parser.parse_args()

    if args.enclenche:
        cmd_enclenche(hint=args.hint)
    elif args.resume:
        cmd_resume()
    elif args.status:
        cmd_status()
    elif args.rapport:
        cmd_rapport(args.siege_id)
    else:
        parser.print_help()
