"""
F01 SENTINEL — Orchestrateur principal
Usage:
  python sentinel.py --prepare  → assemble config dans IN/
  python sentinel.py --iron     → lance les 3 modules de capture
  python sentinel.py --finalize → valide raw_intel.json, check-in IW_CUSTOS
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Chemins relatifs depuis ce fichier
FRÉGATE_ROOT = Path(__file__).parent.parent
MONDE_ROOT = FRÉGATE_ROOT.parent
CORE_ROOT = MONDE_ROOT.parent.parent / "CORE"
sys.path.insert(0, str(CORE_ROOT))
sys.path.insert(0, str(FRÉGATE_ROOT / "CODEBASE"))

IN_DIR = FRÉGATE_ROOT / "IN"
OUT_DIR = FRÉGATE_ROOT / "OUT"
ARCHIVUM = MONDE_ROOT / "ARCHIVUM"
CUSTOS = MONDE_ROOT / "IW_CUSTOS.py"

IN_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)


def cmd_prepare():
    """Lit le liber pour connaître la catégorie à scanner, prépare la config."""
    liber_path = MONDE_ROOT / "liber_api.json"
    if not liber_path.exists():
        print("[F01] ERREUR : liber_api.json introuvable")
        sys.exit(1)

    with open(liber_path) as f:
        liber = json.load(f)

    category = (liber.get("warsmith_brief", {}) or {}).get("categorie_hint") or "data"
    siege_id = liber.get("siege_id", "API-001")

    config = {
        "siege_id": siege_id,
        "category_slug": category,
        "max_pages": 3,
        "max_wrappers": 30,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    config_path = IN_DIR / "sentinel_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"[F01 SENTINEL --prepare] Config prête : catégorie={category}, siège={siege_id}")
    print(f"  → {config_path}")


def cmd_iron():
    """Lance les 3 modules de capture, assemble raw_intel.json."""
    from sentinel_rapid import scrape_category
    from sentinel_gh import search_wrappers
    from sentinel_web import scrape_urls

    config_path = IN_DIR / "sentinel_config.json"
    if not config_path.exists():
        print("[F01] ERREUR : sentinel_config.json manquant — lance --prepare d'abord")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    siege_id = config["siege_id"]
    category = config["category_slug"]

    print(f"[F01 SENTINEL --iron] Scan en cours : {category}...")

    # Module 1 — RapidAPI listings
    print("  → sentinel_rapid : scrape RapidAPI...")
    rapid_results = scrape_category(category, max_pages=config.get("max_pages", 3))
    print(f"     {len(rapid_results)} APIs trouvées")

    # Module 2 — GitHub wrappers pour les 5 premières APIs
    gh_results = []
    for api in rapid_results[:5]:
        host_guess = api.get("slug", "").replace("-", "") + ".p.rapidapi.com"
        print(f"  → sentinel_gh : wrappers pour {host_guess}...")
        gh_data = search_wrappers(host_guess, max_results=config.get("max_wrappers", 30))
        gh_results.append(gh_data)

    # Module 3 — Jina Reader sur docs RapidAPI
    doc_urls = [f"https://rapidapi.com/category/{category}"]
    for api in rapid_results[:3]:
        doc_urls.append(f"https://rapidapi.com/{api.get('provider','')}/api/{api.get('slug','')}")
    print(f"  → sentinel_web : scrape {len(doc_urls)} URLs via Jina...")
    web_results = scrape_urls(doc_urls)

    # Assemblage raw_intel.json
    raw_intel = {
        "siege_id": siege_id,
        "category": category,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rapid_listings": rapid_results,
        "github_wrappers": gh_results,
        "web_pages": web_results
    }

    # Sauvegarde dans ARCHIVUM/targets/[siege_id]/
    targets_dir = ARCHIVUM / "targets" / siege_id
    targets_dir.mkdir(parents=True, exist_ok=True)
    intel_path = targets_dir / "raw_intel.json"
    with open(intel_path, "w") as f:
        json.dump(raw_intel, f, indent=2, ensure_ascii=False)

    # Aussi dans OUT/
    out_path = OUT_DIR / "raw_intel.json"
    with open(out_path, "w") as f:
        json.dump(raw_intel, f, indent=2, ensure_ascii=False)

    print(f"[F01 SENTINEL --iron] raw_intel.json produit")
    print(f"  → ARCHIVUM : {intel_path}")
    print(f"  → OUT : {out_path}")


def cmd_finalize():
    """Valide raw_intel.json, check-in IW_CUSTOS."""
    out_path = OUT_DIR / "raw_intel.json"
    if not out_path.exists():
        print("[F01] ERREUR : raw_intel.json manquant — lance --iron d'abord")
        sys.exit(1)

    with open(out_path) as f:
        intel = json.load(f)

    rapid_count = len(intel.get("rapid_listings", []))
    gh_count = len(intel.get("github_wrappers", []))
    web_count = len(intel.get("web_pages", []))

    print(f"[F01 SENTINEL --finalize] Validation :")
    print(f"  rapid_listings : {rapid_count}")
    print(f"  github_wrappers : {gh_count}")
    print(f"  web_pages : {web_count}")

    if rapid_count == 0 and web_count == 0:
        print("[F01] AVERTISSEMENT : aucune donnée capturée — vérifier la catégorie")

    # Check-in IW_CUSTOS
    if CUSTOS.exists():
        os.system(f'python "{CUSTOS}" --mode check-in --frigate F01 --output "{out_path}"')
    else:
        print(f"[F01] IW_CUSTOS.py introuvable à {CUSTOS}")

    print("[F01 SENTINEL --finalize] OK — passer à F02 BREACHER")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="F01 SENTINEL")
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
