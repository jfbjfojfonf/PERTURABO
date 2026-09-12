"""
F04 HERALD — Génération listings RapidAPI + README GitHub LLM-ready
Usage:
  python herald.py --prepare  → charge warriors.json → prompts listings
  python herald.py --iron     → call_oracle_batch → listings_output.json
  python herald.py --finalize → génère fichiers finaux, check-in, Gate 4
"""
import argparse
import json
import os
import sys
from pathlib import Path

FRÉGATE_ROOT = Path(__file__).parent.parent
MONDE_ROOT = FRÉGATE_ROOT.parent
CORE_ROOT = MONDE_ROOT.parent.parent / "CORE"
sys.path.insert(0, str(CORE_ROOT))

IN_DIR = FRÉGATE_ROOT / "IN"
OUT_DIR = FRÉGATE_ROOT / "OUT"
ARCHIVUM = MONDE_ROOT / "ARCHIVUM"
CONTRACTS = MONDE_ROOT / "CONTRACTS"
CUSTOS = MONDE_ROOT / "IW_CUSTOS.py"

IN_DIR.mkdir(exist_ok=True)
OUT_DIR.mkdir(exist_ok=True)


def build_listing_prompt(warrior: dict, system_prompt: str, iron_contract: str) -> str:
    return f"""{system_prompt}

---

{iron_contract}

---

## MISSION F04 HERALD — Listing RapidAPI + README

Tu es F04 HERALD. Tu crées les contenus marketing pour Iron Warrior {warrior.get('warrior_id')}.

### Données Iron Warrior
- Titre : {warrior.get('api_title', '?')}
- Description : {warrior.get('api_description', '?')}
- Endpoint : {warrior.get('endpoint_path', '/api/v1/search')}
- Prix : {warrior.get('pricing_tier', '$4/month')}
- Tags : {warrior.get('tags_rapidapi', [])}
- Différenciateur : {warrior.get('differentiateur', 'plus rapide et moins cher')}

### Produis UN JSON valide :

{{
  "warrior_id": {warrior.get('warrior_id')},
  "rapidapi_title": "Titre RapidAPI optimisé SEO (< 60 chars, inclut mot-clé concurrent)",
  "rapidapi_description": "Description complète RapidAPI (200-400 chars, mots-clés agents IA)",
  "rapidapi_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "pricing_basic": "Free tier : 1000 req/month",
  "pricing_pro": "{warrior.get('pricing_tier', '$4/month (25k req)')}",
  "pricing_ultra": "$15/month (100k req)",
  "readme_md": "README GitHub complet en Markdown (400-600 chars) avec : titre, description, installation pip, exemple curl, lien RapidAPI, openapi.json référencé, tags LLM-ready)",
  "seo_keywords": ["keyword1", "keyword2", "keyword3"]
}}

Règles :
- rapidapi_title doit contenir le nom de la cible concurrente comme mot-clé
- readme_md doit mentionner explicitement 'AI agent', 'LLM', 'automation'
- Pas de texte hors JSON
"""


def cmd_prepare():
    warriors_path = MONDE_ROOT / "fregates" / "F03_FORGEWARD" / "OUT" / "warriors.json"
    if not warriors_path.exists():
        print("[F04] ERREUR : warriors.json introuvable — F03 doit tourner d'abord")
        sys.exit(1)

    with open(warriors_path) as f:
        data = json.load(f)

    warriors = [w for w in data.get("warriors", []) if w.get("status") != "error"]
    siege_id = data.get("siege_id", "API-001")

    system_prompt = (CONTRACTS / "system_prompt.md").read_text() if (CONTRACTS / "system_prompt.md").exists() else ""
    iron_contract = (CONTRACTS / "iron_prompt.md").read_text() if (CONTRACTS / "iron_prompt.md").exists() else ""

    prompts = []
    for w in warriors:
        prompts.append({
            "warrior_id": w.get("warrior_id"),
            "prompt": build_listing_prompt(w, system_prompt, iron_contract)
        })

    config = {"siege_id": siege_id, "prompts": prompts}
    config_path = IN_DIR / "herald_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"[F04 HERALD --prepare] {len(prompts)} listings à générer")
    print(f"  → {config_path}")


def cmd_iron():
    config_path = IN_DIR / "herald_config.json"
    if not config_path.exists():
        print("[F04] ERREUR : herald_config.json manquant")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    try:
        from ai_gateway import call_oracle_batch
    except ImportError:
        print("[F04] ERREUR : impossible d'importer ai_gateway")
        sys.exit(1)

    prompts_list = [p["prompt"] for p in config["prompts"]]
    warrior_ids = [p["warrior_id"] for p in config["prompts"]]

    print(f"[F04 HERALD --iron] Génération de {len(prompts_list)} listings en parallèle...")
    raw_results = call_oracle_batch("F04", prompts_list, max_workers=5)

    listings = []
    for wid, raw in zip(warrior_ids, raw_results):
        listing = _extract_json(raw)
        if listing:
            listing["warrior_id"] = wid
            listings.append(listing)
            print(f"  warrior_{wid:02d} — {listing.get('rapidapi_title', '?')[:50]} ✓")
        else:
            print(f"  warrior_{wid:02d} — ERREUR parsing")
            listings.append({"warrior_id": wid, "status": "error"})

    out_path = OUT_DIR / "listings_output.json"
    with open(out_path, "w") as f:
        json.dump({"siege_id": config["siege_id"], "listings": listings}, f, indent=2, ensure_ascii=False)

    ok = len([l for l in listings if l.get("status") != "error"])
    print(f"\n[F04 HERALD --iron] {ok}/{len(listings)} listings générés → {out_path}")


def cmd_finalize():
    out_path = OUT_DIR / "listings_output.json"
    if not out_path.exists():
        print("[F04] ERREUR : listings_output.json manquant")
        sys.exit(1)

    with open(out_path) as f:
        data = json.load(f)

    siege_id = data.get("siege_id", "API-001")
    listings = data.get("listings", [])

    # Écrire README.md et listing.md pour chaque warrior
    warriors_dir = ARCHIVUM / "targets" / siege_id / "ironwarriors"
    ready = 0
    for listing in listings:
        if listing.get("status") == "error":
            continue
        wid = listing.get("warrior_id", 0)
        wdir = warriors_dir / f"warrior_{wid:02d}"
        wdir.mkdir(parents=True, exist_ok=True)

        # README.md
        readme = listing.get("readme_md", f"# {listing.get('rapidapi_title', 'API')}\n")
        (wdir / "README.md").write_text(readme, encoding="utf-8")

        # listing_rapidapi.md
        listing_md = f"""# Listing RapidAPI — warrior_{wid:02d}

## Titre
{listing.get('rapidapi_title', '')}

## Description
{listing.get('rapidapi_description', '')}

## Tags
{', '.join(listing.get('rapidapi_tags', []))}

## Pricing
- **Basic** : {listing.get('pricing_basic', 'Free')}
- **Pro** : {listing.get('pricing_pro', '')}
- **Ultra** : {listing.get('pricing_ultra', '')}

## SEO Keywords
{', '.join(listing.get('seo_keywords', []))}
"""
        (wdir / "listing_rapidapi.md").write_text(listing_md, encoding="utf-8")
        ready += 1

    print(f"\n[F04 HERALD --finalize] {ready}/{len(listings)} listings matérialisés")
    print(f"  → {warriors_dir}")

    print("\n" + "=" * 60)
    print("  GATE 4 — RÉCAP FINAL")
    print("=" * 60)
    for listing in listings[:5]:
        if listing.get("status") != "error":
            print(f"  [{listing.get('warrior_id'):02d}] {listing.get('rapidapi_title', '?')[:55]}")
            print(f"       Prix : {listing.get('pricing_pro', '?')}")
    if len(listings) > 5:
        print(f"  ... +{len(listings)-5} autres")
    print("=" * 60)

    if CUSTOS.exists():
        os.system(f'python "{CUSTOS}" --mode check-in --frigate F04 --output "{out_path}"')
        os.system(f'python "{CUSTOS}" --mode gate --gate 4 --decision yes --notes "{ready} listings ready"')

    print("[F04 HERALD --finalize] Gate 4 validée — passer à F05 GRAND COMPASS")


def _extract_json(text: str) -> dict | None:
    import re
    match = re.search(r'\{[\s\S]*\}', text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="F04 HERALD")
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
