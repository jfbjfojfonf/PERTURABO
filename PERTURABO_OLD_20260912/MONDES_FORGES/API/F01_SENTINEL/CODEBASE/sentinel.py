"""
sentinel.py — F01 SENTINEL — Orchestrateur du renseignement multi-source
Usage:
    python sentinel.py --prepare    → initialise le contexte du siège
    python sentinel.py --run        → capture multi-source (RapidAPI + GitHub + Web)
    python sentinel.py --finalize   → Oracle parse le brut, produit raw_intel.json
"""

import argparse
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SENTINEL_DIR = Path(__file__).parent.parent       # F01_SENTINEL/
MONDE_DIR = SENTINEL_DIR.parent                   # MONDES_FORGES/API/
CORE_DIR = MONDE_DIR.parent.parent / "CORE"
IN_DIR = SENTINEL_DIR / "IN"
OUT_DIR = SENTINEL_DIR / "OUT"
IW_CUSTOS_PATH = MONDE_DIR / "IW_CUSTOS.py"
LIBER_PATH = MONDE_DIR / "liber_api.json"
ARCHIVUM_TARGETS = MONDE_DIR / "ARCHIVUM" / "targets"

sys.path.insert(0, str(CORE_DIR))


def _load_local(name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_liber() -> dict:
    return json.loads(LIBER_PATH.read_text(encoding="utf-8")) if LIBER_PATH.exists() else {}


# ─── --prepare ────────────────────────────────────────────────────────────────

def prepare():
    IN_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    liber = load_liber()
    siege_id = liber.get("siege_id", "API-001")
    brief = liber.get("warsmith_brief", {})

    config = {
        "siege_id": siege_id,
        "categorie_hint": brief.get("categorie_hint"),
        "mode": brief.get("mode", "enclenche"),
        "timestamp_prepare": datetime.now(timezone.utc).isoformat()
    }

    (IN_DIR / "sentinel_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[F01 SENTINEL --prepare] Siege ID  : {siege_id}")
    print(f"[F01 SENTINEL --prepare] Categorie : {config['categorie_hint'] or 'ENCLENCHE (auto)'}")


# ─── --run ────────────────────────────────────────────────────────────────────

def run():
    config_path = IN_DIR / "sentinel_config.json"
    if not config_path.exists():
        print("[F01 SENTINEL --run] ERREUR : Lancer --prepare d'abord.")
        sys.exit(1)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    siege_id = config["siege_id"]
    categorie_hint = config.get("categorie_hint")

    print(f"[F01 SENTINEL --run] Siège {siege_id} — capture en cours...")

    sentinel_rapid = _load_local("sentinel_rapid")
    sentinel_gh = _load_local("sentinel_gh")
    sentinel_web = _load_local("sentinel_web")

    # Module 1 — RapidAPI
    print("[F01 SENTINEL] 1/3 RapidAPI scrape...")
    rapid_data = sentinel_rapid.get_top_apis_raw(categorie_hint)

    # Module 2 — GitHub
    print("[F01 SENTINEL] 2/3 GitHub API...")
    gh_data = {}
    if categorie_hint:
        gh_data["primary"] = sentinel_gh.search_wrappers(categorie_hint)
    else:
        for term in ["rapidapi scraper", "rapidapi data extraction", "rapidapi linkedin"]:
            result = sentinel_gh.search_wrappers(term)
            if result["total_wrappers"] > 0:
                gh_data[term] = result

    # Module 3 — Web docs (Jina Reader)
    print("[F01 SENTINEL] 3/3 Documentation web...")
    docs_urls = ["https://rapidapi.com/blog/most-popular-api/"]
    if categorie_hint:
        docs_urls.append(f"https://rapidapi.com/category/{categorie_hint}")
    web_data = sentinel_web.fetch_multiple(docs_urls)
    # Tronquer pour ne pas exploser le JSON
    web_data = {k: (v[:3000] if v else None) for k, v in web_data.items()}

    raw_intel_draft = {
        "siege_id": siege_id,
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "categorie_hint": categorie_hint,
        "rapid_raw": rapid_data,
        "github_intel": gh_data,
        "docs_intel": web_data,
        "status": "raw_captured"
    }

    out_path = OUT_DIR / "raw_intel_draft.json"
    out_path.write_text(json.dumps(raw_intel_draft, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[F01 SENTINEL --run] Draft sauvegardé ({out_path.stat().st_size} bytes)")


# ─── --finalize ───────────────────────────────────────────────────────────────

def finalize():
    draft_path = OUT_DIR / "raw_intel_draft.json"
    if not draft_path.exists():
        print("[F01 SENTINEL --finalize] ERREUR : Lancer --run d'abord.")
        sys.exit(1)

    raw_intel = json.loads(draft_path.read_text(encoding="utf-8"))
    siege_id = raw_intel["siege_id"]

    try:
        from ai_gateway import call_oracle
    except ImportError:
        print(f"[F01 SENTINEL --finalize] ERREUR : ai_gateway.py introuvable dans {CORE_DIR}")
        sys.exit(1)

    print("[F01 SENTINEL --finalize] Oracle parse les données brutes...")

    rapid_content = json.dumps(raw_intel.get("rapid_raw", {}), ensure_ascii=False)[:6000]
    gh_content = json.dumps(raw_intel.get("github_intel", {}), ensure_ascii=False)[:2000]

    parse_prompt = f"""Tu es F01 SENTINEL du système PERTURABO.
Tu reçois des données brutes scrapées depuis RapidAPI et GitHub.
Extrais une liste structurée d'APIs candidates à assiéger.

## DONNÉES BRUTES RAPIDAPI
{rapid_content}

## DONNÉES GITHUB
{gh_content}

## INSTRUCTIONS
Extrais 5 à 10 APIs RapidAPI candidates. Utilise UNIQUEMENT les données visibles.
Si une donnée est absente, mets null.

Réponds UNIQUEMENT avec ce JSON :
{{
  "apis_candidates": [
    {{
      "nom": "string",
      "categorie": "string",
      "popularite_score": null,
      "latence_ms": null,
      "service_level_pct": null,
      "pricing_tiers": [],
      "endpoint_count": null,
      "wrappers_github_approx": null,
      "signal_fort": "string — pourquoi cette API est une cible potentielle"
    }}
  ],
  "categorie_dominante": "string",
  "signal_global": "string — résumé en 1 phrase de ce que le scan révèle"
}}"""

    parsed_result = call_oracle("F01", parse_prompt)

    parsed_data = {"apis_candidates": [], "signal_global": "Oracle non disponible"}
    if parsed_result:
        clean = parsed_result.strip()
        if clean.startswith("```"):
            lines = clean.split("\n")
            end = -1 if lines[-1].strip() == "```" else len(lines)
            clean = "\n".join(lines[1:end])
        try:
            parsed_data = json.loads(clean)
        except json.JSONDecodeError:
            print("[F01 SENTINEL --finalize] AVERTISSEMENT : parsing Oracle échoué, données brutes conservées.")

    raw_intel["parsed"] = parsed_data
    raw_intel["status"] = "intel_captured"
    raw_intel["scan_timestamp_finalize"] = datetime.now(timezone.utc).isoformat()

    target_dir = ARCHIVUM_TARGETS / siege_id
    target_dir.mkdir(parents=True, exist_ok=True)
    final_path = target_dir / "raw_intel.json"
    final_path.write_text(json.dumps(raw_intel, indent=2, ensure_ascii=False), encoding="utf-8")

    candidates = len(parsed_data.get("apis_candidates", []))
    print(f"[F01 SENTINEL --finalize] raw_intel.json → {final_path}")
    print(f"APIs candidates : {candidates}")
    print(f"Signal global   : {parsed_data.get('signal_global', 'N/A')}")

    result = subprocess.run(
        [sys.executable, str(IW_CUSTOS_PATH),
         "--mode", "check-in", "--frigate", "F01", "--output", str(final_path)],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(result.stdout.strip())
    else:
        print(f"[F01 SENTINEL] AVERTISSEMENT IW_CUSTOS : {result.stderr.strip()}")


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="F01 SENTINEL — Renseignement multi-source")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--run", action="store_true")
    group.add_argument("--finalize", action="store_true")
    args = parser.parse_args()

    if args.prepare: prepare()
    elif args.run: run()
    elif args.finalize: finalize()


if __name__ == "__main__":
    main()
