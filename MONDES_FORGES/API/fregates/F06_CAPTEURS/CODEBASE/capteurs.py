"""
F06 CAPTEURS — Monitoring post-siège des Iron Warriors
Usage:
  python capteurs.py --init --siege-id API-001   → initialise le tracking des warriors
  python capteurs.py --scan --siege-id API-001   → scan quotidien des métriques
  python capteurs.py --report --siege-id API-001 → rapport de survie + update rules/
"""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

FRÉGATE_ROOT = Path(__file__).parent.parent
MONDE_ROOT = FRÉGATE_ROOT.parent
CORE_ROOT = MONDE_ROOT.parent.parent / "CORE"
sys.path.insert(0, str(CORE_ROOT))

IN_DIR = FRÉGATE_ROOT / "IN"
OUT_DIR = FRÉGATE_ROOT / "OUT"
ARCHIVUM = MONDE_ROOT / "ARCHIVUM"
LEDGERS = ARCHIVUM / "ledgers"
RULES = ARCHIVUM / "rules"
CUSTOS = MONDE_ROOT / "IW_CUSTOS.py"

IN_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)
LEDGERS.mkdir(parents=True, exist_ok=True)
RULES.mkdir(parents=True, exist_ok=True)

GITHUB_API = "https://api.github.com"

# Seuils de classification
SEUIL_VIVANT = 3          # abonnés RapidAPI minimum pour être "vivant"
SEUIL_GAGNANT = 10        # abonnés pour être classé "gagnant"
SEUIL_MORT = 30           # jours sans activité avant classification "mort"


def _gh_headers():
    token = os.getenv("GITHUB_TOKEN", "")
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }


def fetch_github_metrics(repo_owner: str, repo_name: str) -> dict:
    """Récupère les métriques GitHub d'un repo."""
    import urllib.request
    import urllib.error

    if not repo_owner or not repo_name:
        return {"stars": 0, "forks": 0, "open_issues": 0}

    url = f"{GITHUB_API}/repos/{repo_owner}/{repo_name}"
    req = urllib.request.Request(url, headers=_gh_headers())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return {
                "stars": data.get("stargazers_count", 0),
                "forks": data.get("forks_count", 0),
                "open_issues": data.get("open_issues_count", 0),
                "pushed_at": data.get("pushed_at", "")
            }
    except Exception as e:
        return {"stars": 0, "forks": 0, "open_issues": 0, "error": str(e)[:100]}


def fetch_rapidapi_metrics(api_slug: str) -> dict:
    """
    Tente de récupérer les métriques RapidAPI via scraping minimal.
    RapidAPI n'expose pas d'API publique pour les stats providers.
    On retourne des données fictives si non disponibles — à remplacer
    par un scraping manuel ou une intégration Provider Dashboard.
    """
    # Note : RapidAPI Provider Dashboard est accessible authentifié seulement.
    # Ce module sert de placeholder — le Warsmith met à jour manuellement
    # via la commande --scan avec les données du Provider Dashboard.
    return {
        "subscribers": 0,
        "requests_30d": 0,
        "popularity_score": 0.0,
        "note": "mise_a_jour_manuelle_requise"
    }


def cmd_init(siege_id: str):
    """Initialise le fichier de tracking pour un siège."""
    deploy_path = MONDE_ROOT / "fregates" / "F05_GRAND_COMPASS" / "OUT" / "deploy_results.json"
    if not deploy_path.exists():
        print(f"[F06] ERREUR : deploy_results.json introuvable — F05 doit tourner d'abord")
        sys.exit(1)

    with open(deploy_path) as f:
        deploy_data = json.load(f)

    results = deploy_data.get("results", [])
    now = datetime.now(timezone.utc).isoformat()

    warriors_tracking = []
    for r in results:
        if r.get("status") != "deployed":
            continue

        github_url = r.get("github_url", "")
        repo_parts = github_url.replace("https://github.com/", "").split("/") if github_url else []
        owner = repo_parts[0] if len(repo_parts) > 0 else ""
        repo_name = repo_parts[1] if len(repo_parts) > 1 else ""

        warriors_tracking.append({
            "warrior_id": r["warrior_id"],
            "repo_owner": owner,
            "repo_name": repo_name,
            "github_url": github_url,
            "railway_deploy_url": r.get("railway_deploy_url", ""),
            "rapidapi_slug": "",  # à remplir après publication sur RapidAPI
            "deployed_at": now,
            "status": "deployed",  # deployed → vivant → gagnant | mort
            "metrics_history": [],
            "last_scan": None,
            "days_since_deploy": 0
        })

    ledger_path = LEDGERS / f"{siege_id}_ledger.json"
    ledger = {
        "siege_id": siege_id,
        "initialized_at": now,
        "warriors": warriors_tracking
    }
    with open(ledger_path, "w") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)

    print(f"[F06 CAPTEURS --init] {len(warriors_tracking)} warriors enregistrés")
    print(f"  → {ledger_path}")
    print("\n  ACTION REQUISE :")
    print("  1. Publie chaque API sur RapidAPI avec listing_rapidapi.md")
    print(f"  2. Remplis le champ 'rapidapi_slug' dans {ledger_path}")
    print("  3. Lance 'python capteurs.py --scan' quotidiennement pour le monitoring")


def cmd_scan(siege_id: str, manual_update: dict = None):
    """Scan quotidien : met à jour les métriques de chaque warrior."""
    ledger_path = LEDGERS / f"{siege_id}_ledger.json"
    if not ledger_path.exists():
        print(f"[F06] ERREUR : {ledger_path} introuvable — lance --init d'abord")
        sys.exit(1)

    with open(ledger_path) as f:
        ledger = json.load(f)

    now = datetime.now(timezone.utc)
    updated = 0

    for warrior in ledger["warriors"]:
        wid = warrior["warrior_id"]
        print(f"  [F06] Scan warrior_{wid:02d}...")

        # Métriques GitHub
        gh_metrics = fetch_github_metrics(warrior.get("repo_owner", ""), warrior.get("repo_name", ""))

        # Métriques RapidAPI (manuelle ou automatique)
        if manual_update and str(wid) in manual_update:
            rapidapi_metrics = manual_update[str(wid)]
        else:
            rapidapi_metrics = fetch_rapidapi_metrics(warrior.get("rapidapi_slug", ""))

        # Calcul des jours depuis le deploy
        if warrior.get("deployed_at"):
            deployed_dt = datetime.fromisoformat(warrior["deployed_at"].replace("Z", "+00:00"))
            days = (now - deployed_dt).days
        else:
            days = 0

        warrior["days_since_deploy"] = days
        warrior["last_scan"] = now.isoformat()

        # Mise à jour de l'historique
        snapshot = {
            "date": now.strftime("%Y-%m-%d"),
            "stars": gh_metrics.get("stars", 0),
            "forks": gh_metrics.get("forks", 0),
            "subscribers": rapidapi_metrics.get("subscribers", 0),
            "requests_30d": rapidapi_metrics.get("requests_30d", 0),
            "popularity_score": rapidapi_metrics.get("popularity_score", 0.0)
        }
        warrior["metrics_history"].append(snapshot)

        # Classification automatique
        subscribers = rapidapi_metrics.get("subscribers", 0)
        if subscribers >= SEUIL_GAGNANT:
            warrior["status"] = "gagnant"
        elif subscribers >= SEUIL_VIVANT:
            warrior["status"] = "vivant"
        elif days >= SEUIL_MORT and subscribers == 0:
            warrior["status"] = "mort"
        else:
            warrior["status"] = "deployed"

        updated += 1
        time.sleep(0.2)

    with open(ledger_path, "w") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)

    print(f"\n[F06 CAPTEURS --scan] {updated} warriors scannés → {ledger_path}")
    _print_scan_summary(ledger)


def cmd_report(siege_id: str):
    """Rapport de survie + mise à jour ARCHIVUM/rules/ avec les patterns gagnants."""
    ledger_path = LEDGERS / f"{siege_id}_ledger.json"
    if not ledger_path.exists():
        print(f"[F06] ERREUR : {ledger_path} introuvable")
        sys.exit(1)

    with open(ledger_path) as f:
        ledger = json.load(f)

    warriors = ledger.get("warriors", [])
    gagnants = [w for w in warriors if w["status"] == "gagnant"]
    vivants = [w for w in warriors if w["status"] == "vivant"]
    morts = [w for w in warriors if w["status"] == "mort"]
    deployes = [w for w in warriors if w["status"] == "deployed"]

    print("\n" + "=" * 70)
    print(f"  RAPPORT CAPTEURS — Siège {siege_id}")
    print("=" * 70)
    print(f"  Total warriors : {len(warriors)}")
    print(f"  Gagnants (10+ abonnés) : {len(gagnants)}")
    print(f"  Vivants  (3-9 abonnés) : {len(vivants)}")
    print(f"  En attente              : {len(deployes)}")
    print(f"  Morts (0 abonné, 30j+) : {len(morts)}")
    print("=" * 70)

    if gagnants:
        print("\n  GAGNANTS — Patterns à capitaliser :")
        for w in gagnants:
            last = w["metrics_history"][-1] if w["metrics_history"] else {}
            print(f"  warrior_{w['warrior_id']:02d} — {w.get('repo_name', '?')}")
            print(f"    Abonnés : {last.get('subscribers', 0)} | Stars : {last.get('stars', 0)}")

    # Mise à jour ARCHIVUM/rules/
    if gagnants:
        _update_rules(siege_id, gagnants, ledger)

    # Rapport JSON
    report = {
        "siege_id": siege_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": len(warriors),
            "gagnants": len(gagnants),
            "vivants": len(vivants),
            "morts": len(morts),
            "taux_survie_pct": round((len(gagnants) + len(vivants)) / max(len(warriors), 1) * 100, 1)
        },
        "gagnants": gagnants,
        "patterns_extraits": len(gagnants) > 0
    }
    report_path = OUT_DIR / f"{siege_id}_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    taux = report["summary"]["taux_survie_pct"]
    print(f"\n  Taux de survie : {taux}%")
    print(f"  → Rapport complet : {report_path}")
    print("=" * 70)

    # Check-in IW_CUSTOS — siège completé
    if CUSTOS.exists():
        os.system(f'python "{CUSTOS}" --mode check-in --frigate F06 --output "{report_path}"')

    return report


def _update_rules(siege_id: str, gagnants: list, ledger: dict):
    """
    Extrait les patterns des warriors gagnants et met à jour ARCHIVUM/rules/.
    Chaque pattern devient une règle pour les prochains sièges.
    """
    rules_path = RULES / f"patterns_gagnants.md"
    existing = rules_path.read_text(encoding="utf-8") if rules_path.exists() else "# Patterns Gagnants — Monde-Forge API\n\n"

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_section = f"\n## Siège {siege_id} — {now}\n\n"

    for w in gagnants:
        last = w["metrics_history"][-1] if w["metrics_history"] else {}
        new_section += f"### warrior_{w['warrior_id']:02d} — {w.get('repo_name', '?')}\n"
        new_section += f"- Abonnés : {last.get('subscribers', 0)}\n"
        new_section += f"- Stars GitHub : {last.get('stars', 0)}\n"
        new_section += f"- Requêtes 30j : {last.get('requests_30d', 0)}\n"
        new_section += f"- Jours pour atteindre le seuil : {w.get('days_since_deploy', 0)}\n\n"

    rules_path.write_text(existing + new_section, encoding="utf-8")
    print(f"\n  [F06] ARCHIVUM/rules/patterns_gagnants.md mis à jour ({len(gagnants)} patterns)")

    # Archiver le ledger complet dans ARCHIVUM/ledgers/
    archive_path = LEDGERS / f"{siege_id}_archive_{datetime.now(timezone.utc).strftime('%Y%m%d')}.json"
    import shutil
    src = LEDGERS / f"{siege_id}_ledger.json"
    if src.exists():
        shutil.copy2(src, archive_path)
        print(f"  [F06] Ledger archivé → {archive_path}")


def _print_scan_summary(ledger: dict):
    warriors = ledger.get("warriors", [])
    print("\n  Statuts :")
    for w in warriors:
        last = w["metrics_history"][-1] if w["metrics_history"] else {}
        icon = {"gagnant": "★", "vivant": "●", "mort": "✗", "deployed": "○"}.get(w["status"], "?")
        print(f"  {icon} warrior_{w['warrior_id']:02d} — sub:{last.get('subscribers',0)} stars:{last.get('stars',0)} ({w['status']})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="F06 CAPTEURS")
    parser.add_argument("--init", action="store_true", help="Initialiser le tracking")
    parser.add_argument("--scan", action="store_true", help="Scan quotidien des métriques")
    parser.add_argument("--report", action="store_true", help="Générer le rapport de survie")
    parser.add_argument("--siege-id", default="API-001", help="ID du siège à monitorer")
    parser.add_argument("--manual-update", default=None, help="JSON de métriques manuelles {warrior_id: {subscribers:X}}")
    args = parser.parse_args()

    manual = json.loads(args.manual_update) if args.manual_update else None

    if args.init:
        cmd_init(args.siege_id)
    elif args.scan:
        cmd_scan(args.siege_id, manual_update=manual)
    elif args.report:
        cmd_report(args.siege_id)
    else:
        parser.print_help()
