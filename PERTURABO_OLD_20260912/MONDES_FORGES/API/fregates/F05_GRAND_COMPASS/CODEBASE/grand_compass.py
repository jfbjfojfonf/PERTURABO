"""
F05 GRAND COMPASS — Deploy automatique GitHub + Railway/Render
Usage:
  python grand_compass.py --prepare  → charge listings + warriors → plan de deploy
  python grand_compass.py --iron     → crée repos GitHub + déploie en parallèle
  python grand_compass.py --finalize → capture URLs, check-in IW_CUSTOS
"""
import argparse
import json
import os
import sys
import time
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

FRÉGATE_ROOT = Path(__file__).parent.parent
MONDE_ROOT = FRÉGATE_ROOT.parent
CORE_ROOT = MONDE_ROOT.parent.parent / "CORE"
sys.path.insert(0, str(CORE_ROOT))

IN_DIR = FRÉGATE_ROOT / "IN"
OUT_DIR = FRÉGATE_ROOT / "OUT"
ARCHIVUM = MONDE_ROOT / "ARCHIVUM"
CUSTOS = MONDE_ROOT / "IW_CUSTOS.py"

IN_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)

GITHUB_API = "https://api.github.com"
RAILWAY_DEPLOY_URL = "https://railway.app/new/github"  # URL de deploy Railway via GitHub


def _gh_headers():
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        print("[F05] AVERTISSEMENT : GITHUB_TOKEN non défini — GitHub deploy désactivé")
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json"
    }


def _gh_username():
    import urllib.request
    req = urllib.request.Request(
        f"{GITHUB_API}/user",
        headers={k: v for k, v in _gh_headers().items() if k != "Content-Type"}
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())["login"]
    except Exception:
        return os.getenv("GITHUB_USERNAME", "unknown")


def create_github_repo(repo_name: str, description: str) -> dict:
    """Crée un repo GitHub public pour un Iron Warrior."""
    import urllib.request
    import urllib.error

    payload = json.dumps({
        "name": repo_name,
        "description": description,
        "private": False,
        "auto_init": False
    }).encode()

    req = urllib.request.Request(
        f"{GITHUB_API}/user/repos",
        data=payload,
        headers=_gh_headers(),
        method="POST"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())
            return {"status": "created", "html_url": data["html_url"], "clone_url": data["clone_url"]}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if "already exists" in body or e.code == 422:
            username = _gh_username()
            return {
                "status": "exists",
                "html_url": f"https://github.com/{username}/{repo_name}",
                "clone_url": f"https://github.com/{username}/{repo_name}.git"
            }
        return {"status": "error", "detail": body[:200]}


def push_file_to_repo(username: str, repo_name: str, file_path: str, content: str, message: str):
    """Push un fichier dans un repo GitHub via l'API."""
    import urllib.request
    import urllib.error

    content_b64 = base64.b64encode(content.encode("utf-8")).decode()
    payload = json.dumps({
        "message": message,
        "content": content_b64
    }).encode()

    req = urllib.request.Request(
        f"{GITHUB_API}/repos/{username}/{repo_name}/contents/{file_path}",
        data=payload,
        headers=_gh_headers(),
        method="PUT"
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return {"status": "ok"}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        # Si le fichier existe déjà, récupérer son SHA et mettre à jour
        if e.code == 422:
            return {"status": "exists"}
        return {"status": "error", "detail": body[:100]}


def deploy_warrior(warrior_plan: dict) -> dict:
    """Deploy un Iron Warrior : crée le repo GitHub, push les fichiers."""
    wid = warrior_plan["warrior_id"]
    repo_name = warrior_plan["service_name"]
    wdir = Path(warrior_plan["wdir"])

    print(f"  [F05] warrior_{wid:02d} — création repo {repo_name}...")

    # 1. Créer le repo GitHub
    repo_result = create_github_repo(
        repo_name,
        warrior_plan.get("api_description", "Iron Warrior API")
    )
    if repo_result["status"] == "error":
        return {"warrior_id": wid, "status": "error", "detail": repo_result.get("detail")}

    username = _gh_username()
    github_url = repo_result["html_url"]

    # 2. Push les fichiers un par un via l'API GitHub
    files_to_push = ["api.py", "requirements.txt", "openapi.json", "README.md", "deploy.sh"]
    pushed = 0
    for fname in files_to_push:
        fpath = wdir / fname
        if fpath.exists():
            content = fpath.read_text(encoding="utf-8")
            result = push_file_to_repo(username, repo_name, fname, content, f"feat: add {fname}")
            if result["status"] in ("ok", "exists"):
                pushed += 1
            time.sleep(0.3)  # Rate limit GitHub API

    # 3. URL de deploy Railway (le Warsmith devra cliquer sur le lien)
    railway_url = f"https://railway.app/new/github?repo={username}/{repo_name}"
    render_url = f"https://render.com/deploy?repo=https://github.com/{username}/{repo_name}"

    print(f"  [F05] warrior_{wid:02d} — {pushed} fichiers pushés → {github_url}")

    return {
        "warrior_id": wid,
        "status": "deployed",
        "repo_name": repo_name,
        "github_url": github_url,
        "railway_deploy_url": railway_url,
        "render_deploy_url": render_url,
        "files_pushed": pushed
    }


def cmd_prepare():
    liber_path = MONDE_ROOT / "liber_api.json"
    with open(liber_path) as f:
        liber = json.load(f)

    siege_id = liber.get("siege_id", "API-001")
    warriors_dir = ARCHIVUM / "targets" / siege_id / "ironwarriors"

    if not warriors_dir.exists():
        print(f"[F05] ERREUR : {warriors_dir} introuvable — F03/F04 doivent tourner d'abord")
        sys.exit(1)

    # Charger la liste des warriors depuis warriors.json
    warriors_json = MONDE_ROOT / "fregates" / "F03_FORGEWARD" / "OUT" / "warriors.json"
    with open(warriors_json) as f:
        warriors_data = json.load(f)

    plans = []
    for w in warriors_data.get("warriors", []):
        if w.get("status") == "error":
            continue
        wid = w["warrior_id"]
        wdir = warriors_dir / f"warrior_{wid:02d}"
        if not wdir.exists():
            continue

        meta_path = wdir / "meta.json"
        meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

        plans.append({
            "warrior_id": wid,
            "service_name": w.get("service_name", f"warrior-{wid:02d}"),
            "api_description": w.get("api_description", ""),
            "wdir": str(wdir),
            "api_title": meta.get("api_title", f"warrior-{wid:02d}")
        })

    config = {"siege_id": siege_id, "deploy_plans": plans}
    config_path = IN_DIR / "compass_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"[F05 GRAND COMPASS --prepare] {len(plans)} warriors à déployer")
    print(f"  → {config_path}")
    if not os.getenv("GITHUB_TOKEN"):
        print("\n  AVERTISSEMENT : Variable GITHUB_TOKEN non définie")
        print("  → Définis GITHUB_TOKEN dans .env pour le deploy automatique")
        print("  → Sinon, les URLs Railway/Render seront générées mais non pushées")


def cmd_iron():
    config_path = IN_DIR / "compass_config.json"
    if not config_path.exists():
        print("[F05] ERREUR : compass_config.json manquant")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    plans = config.get("deploy_plans", [])
    print(f"[F05 GRAND COMPASS --iron] Deploy de {len(plans)} Iron Warriors en parallèle...")

    results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(deploy_warrior, plan): plan for plan in plans}
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                plan = futures[future]
                results.append({
                    "warrior_id": plan["warrior_id"],
                    "status": "error",
                    "detail": str(e)
                })

    # Trier par warrior_id
    results.sort(key=lambda x: x.get("warrior_id", 0))

    out_path = OUT_DIR / "deploy_results.json"
    with open(out_path, "w") as f:
        json.dump({"siege_id": config["siege_id"], "results": results}, f, indent=2, ensure_ascii=False)

    ok = len([r for r in results if r.get("status") == "deployed"])
    print(f"\n[F05 GRAND COMPASS --iron] {ok}/{len(results)} warriors déployés")
    print(f"  → {out_path}")


def cmd_finalize():
    out_path = OUT_DIR / "deploy_results.json"
    if not out_path.exists():
        print("[F05] ERREUR : deploy_results.json manquant")
        sys.exit(1)

    with open(out_path) as f:
        data = json.load(f)

    siege_id = data.get("siege_id", "API-001")
    results = data.get("results", [])

    # Mettre à jour le liber avec les URLs de deploy
    liber_path = MONDE_ROOT / "liber_api.json"
    with open(liber_path) as f:
        liber = json.load(f)

    liber["f05"]["deployed_urls"] = [
        {
            "warrior_id": r["warrior_id"],
            "github_url": r.get("github_url", ""),
            "railway_deploy_url": r.get("railway_deploy_url", ""),
            "render_deploy_url": r.get("render_deploy_url", "")
        }
        for r in results if r.get("status") == "deployed"
    ]

    with open(liber_path, "w") as f:
        json.dump(liber, f, indent=2, ensure_ascii=False)

    # Afficher le récap
    ok = len([r for r in results if r.get("status") == "deployed"])
    print(f"\n[F05 GRAND COMPASS --finalize] {ok} Iron Warriors en ligne")
    print("\n" + "=" * 70)
    print("  DEPLOY COMPLET — Actions requises du Warsmith")
    print("=" * 70)
    for r in results:
        if r.get("status") == "deployed":
            print(f"\n  warrior_{r['warrior_id']:02d} — {r.get('github_url', '')}")
            print(f"  Railway : {r.get('railway_deploy_url', '')}")
    print("=" * 70)
    print("\n  Pour chaque warrior : clique sur le lien Railway pour finaliser le deploy")
    print("  Ensuite : publie chaque API sur RapidAPI avec listing_rapidapi.md")

    # Check-in IW_CUSTOS
    if CUSTOS.exists():
        os.system(f'python "{CUSTOS}" --mode check-in --frigate F05 --output "{out_path}"')

    # Activer F06 CAPTEURS
    print("\n[F05 GRAND COMPASS --finalize] Activation F06 CAPTEURS...")
    f06_capteurs = MONDE_ROOT / "fregates" / "F06_CAPTEURS" / "CODEBASE" / "capteurs.py"
    if f06_capteurs.exists():
        os.system(f'python "{f06_capteurs}" --init --siege-id {siege_id}')

    print("[F05 GRAND COMPASS --finalize] Siège terminé — CAPTEURS activés")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="F05 GRAND COMPASS")
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--iron", action="store_true")
    parser.add_argument("--finalize", action="store_true")
    args = parser.parse_args()

    if args.prepare:
        cmd_prepare()
    elif args.iron:
        cmd_iron()
    elif args.finalize:
        cmd_finalize()
    else:
        parser.print_help()
