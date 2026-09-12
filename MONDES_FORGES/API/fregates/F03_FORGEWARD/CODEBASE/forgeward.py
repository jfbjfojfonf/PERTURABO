"""
F03 FORGEWARD — Génération des 20 Iron Warriors en parallèle
Usage:
  python forgeward.py --prepare  → charge les 20 angles F02 → 20 prompts
  python forgeward.py --iron     → call_oracle_batch → 20 codes FastAPI
  python forgeward.py --finalize → valide syntaxe, check-in IW_CUSTOS, Gate 3
"""
import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
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


FASTAPI_TEMPLATE = """
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx
import os

app = FastAPI(
    title="{api_title}",
    description="{api_description}",
    version="1.0.0"
)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")

@app.get("/health")
def health():
    return {{"status": "online", "version": "1.0.0"}}

@app.get("{endpoint_path}")
async def main_endpoint(
    query: str = Query(..., description="Search query"),
    country: str = Query("US", description="Target country code"),
    limit: int = Query(10, ge=1, le=100, description="Max results")
):
    \"\"\"
    {endpoint_description}
    \"\"\"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                "{target_url}",
                params={{"query": query, "country": country, "limit": limit}},
                headers={{
                    "x-rapidapi-key": RAPIDAPI_KEY,
                    "x-rapidapi-host": "{rapidapi_host}"
                }}
            )
            resp.raise_for_status()
            return JSONResponse(content=resp.json())
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=e.response.status_code, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
"""

REQUIREMENTS_TEMPLATE = "fastapi>=0.110.0\nuvicorn[standard]>=0.27.0\nhttpx>=0.26.0\npython-dotenv>=1.0.0\n"

DEPLOY_SH_TEMPLATE = """#!/bin/bash
# Deploy Iron Warrior {warrior_id} — {api_title}
# Railway deployment
railway up --service {service_name}
"""

OPENAPI_TEMPLATE = {
    "openapi": "3.0.0",
    "info": {
        "title": "{api_title}",
        "description": "{api_description}",
        "version": "1.0.0"
    },
    "paths": {
        "{endpoint_path}": {
            "get": {
                "summary": "{endpoint_description}",
                "parameters": [
                    {"name": "query", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "country", "in": "query", "required": False, "schema": {"type": "string", "default": "US"}},
                    {"name": "limit", "in": "query", "required": False, "schema": {"type": "integer", "default": 10}}
                ],
                "responses": {
                    "200": {"description": "Success"},
                    "500": {"description": "Server error"}
                }
            }
        }
    }
}


def build_warrior_prompt(angle: dict, cible: dict, system_prompt: str, iron_contract: str) -> str:
    return f"""{system_prompt}

---

{iron_contract}

---

## MISSION F03 FORGEWARD — Iron Warrior {angle['id']}

Tu es F03 FORGEWARD. Tu dois générer UN Iron Warrior complet.

### Cible API à concurrencer
- Nom : {cible.get('cible_nom', 'API cible')}
- Host RapidAPI : {cible.get('cible_host', 'api.p.rapidapi.com')}
- Faille principale : {cible.get('faille_principale', 'latence élevée')}
- Prix du leader : {cible.get('prix_leader', '$X/month')}

### Angle d'attaque
- ID : {angle['id']}
- Type : {angle['type']}
- Description : {angle.get('description', '')}
- Prix suggéré : {angle.get('prix_suggere', '$4/month')}

### Ce que tu dois produire
Génère UNIQUEMENT un JSON valide avec ces champs :

{{
  "warrior_id": {angle['id']},
  "angle_type": "{angle['type']}",
  "api_title": "Nom commercial de l'API (< 60 chars)",
  "api_description": "Description courte (< 120 chars)",
  "endpoint_path": "/api/v1/[action]",
  "endpoint_description": "Ce que fait cet endpoint",
  "target_url": "URL source à appeler",
  "rapidapi_host": "{cible.get('cible_host', 'api.p.rapidapi.com')}",
  "service_name": "nom-service-railway",
  "api_py_code": "code FastAPI complet (uvicorn api:app)",
  "requirements_txt": "fastapi>=0.110.0\\nuvicorn[standard]>=0.27.0\\nhttpx>=0.26.0",
  "pricing_tier": "{angle.get('prix_suggere', '$4/month (25k req)')}",
  "tags_rapidapi": ["tag1", "tag2", "tag3"],
  "differentiateur": "Ce qui rend cette variante meilleure que le leader"
}}

Règles absolues :
- api_py_code doit être du Python valide (FastAPI + httpx async)
- endpoint_path commence par /api/v1/
- service_name en kebab-case
- 3-5 tags RapidAPI pertinents
"""


def cmd_prepare():
    liber_path = MONDE_ROOT / "liber_api.json"
    with open(liber_path) as f:
        liber = json.load(f)

    siege_id = liber.get("siege_id", "API-001")
    breacher_path = MONDE_ROOT / "fregates" / "F02_BREACHER" / "OUT" / "breacher_output.json"

    if not breacher_path.exists():
        print(f"[F03] ERREUR : breacher_output.json introuvable")
        sys.exit(1)

    with open(breacher_path) as f:
        breacher = json.load(f)

    angles = breacher.get("angles_attaque", [])[:20]
    if not angles:
        print("[F03] ERREUR : aucun angle d'attaque dans breacher_output.json")
        sys.exit(1)

    system_prompt = (CONTRACTS / "system_prompt.md").read_text() if (CONTRACTS / "system_prompt.md").exists() else ""
    iron_contract = (CONTRACTS / "iron_prompt.md").read_text() if (CONTRACTS / "iron_prompt.md").exists() else ""

    prompts = []
    for angle in angles:
        prompt = build_warrior_prompt(angle, breacher, system_prompt, iron_contract)
        prompts.append({"angle_id": angle["id"], "angle_type": angle["type"], "prompt": prompt})

    config = {"siege_id": siege_id, "prompts": prompts, "cible": breacher}
    config_path = IN_DIR / "forgeward_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"[F03 FORGEWARD --prepare] {len(prompts)} prompts prêts")
    print(f"  → {config_path}")


def cmd_iron():
    config_path = IN_DIR / "forgeward_config.json"
    if not config_path.exists():
        print("[F03] ERREUR : forgeward_config.json manquant — lance --prepare d'abord")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    try:
        from ai_gateway import call_oracle_batch
    except ImportError:
        print("[F03] ERREUR : impossible d'importer ai_gateway depuis CORE/")
        sys.exit(1)

    prompts_list = [p["prompt"] for p in config["prompts"]]
    angle_ids = [p["angle_id"] for p in config["prompts"]]

    print(f"[F03 FORGEWARD --iron] Forge de {len(prompts_list)} Iron Warriors en parallèle...")
    raw_results = call_oracle_batch("F03", prompts_list, max_workers=5)

    warriors = []
    for i, (angle_id, raw) in enumerate(zip(angle_ids, raw_results)):
        warrior = _extract_json(raw)
        if warrior:
            warrior["warrior_id"] = angle_id
            warriors.append(warrior)
            print(f"  [{i+1:02d}] warrior_{angle_id:02d} — {warrior.get('api_title', '?')} ✓")
        else:
            print(f"  [{i+1:02d}] warrior_{angle_id:02d} — ERREUR parsing")
            warriors.append({"warrior_id": angle_id, "status": "error", "raw": raw[:200]})

    out_path = OUT_DIR / "warriors.json"
    with open(out_path, "w") as f:
        json.dump({"siege_id": config["siege_id"], "warriors": warriors}, f, indent=2, ensure_ascii=False)

    ok = len([w for w in warriors if w.get("status") != "error"])
    print(f"\n[F03 FORGEWARD --iron] {ok}/{len(warriors)} Iron Warriors forgés")
    print(f"  → {out_path}")


def cmd_finalize():
    out_path = OUT_DIR / "warriors.json"
    if not out_path.exists():
        print("[F03] ERREUR : warriors.json manquant — lance --iron d'abord")
        sys.exit(1)

    with open(out_path) as f:
        data = json.load(f)

    warriors = data.get("warriors", [])
    siege_id = data.get("siege_id", "API-001")

    # Générer les fichiers pour chaque warrior valide
    warriors_dir = ARCHIVUM / "targets" / siege_id / "ironwarriors"
    warriors_dir.mkdir(parents=True, exist_ok=True)

    ready = 0
    for w in warriors:
        if w.get("status") == "error":
            continue
        wid = w.get("warrior_id", 0)
        wdir = warriors_dir / f"warrior_{wid:02d}"
        wdir.mkdir(exist_ok=True)

        # api.py
        (wdir / "api.py").write_text(w.get("api_py_code", ""), encoding="utf-8")
        # requirements.txt
        (wdir / "requirements.txt").write_text(w.get("requirements_txt", REQUIREMENTS_TEMPLATE), encoding="utf-8")
        # openapi.json
        spec = dict(OPENAPI_TEMPLATE)
        spec["info"]["title"] = w.get("api_title", "API")
        spec["info"]["description"] = w.get("api_description", "")
        (wdir / "openapi.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")
        # deploy.sh
        deploy = DEPLOY_SH_TEMPLATE.format(
            warrior_id=wid,
            api_title=w.get("api_title", ""),
            service_name=w.get("service_name", f"warrior-{wid:02d}")
        )
        (wdir / "deploy.sh").write_text(deploy, encoding="utf-8")
        # meta.json
        (wdir / "meta.json").write_text(json.dumps({
            "warrior_id": wid,
            "api_title": w.get("api_title"),
            "pricing_tier": w.get("pricing_tier"),
            "tags_rapidapi": w.get("tags_rapidapi", []),
            "differentiateur": w.get("differentiateur")
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        ready += 1

    print(f"\n[F03 FORGEWARD --finalize] {ready}/{len(warriors)} Iron Warriors matérialisés")
    print(f"  → {warriors_dir}")

    if CUSTOS.exists():
        os.system(f'python "{CUSTOS}" --mode check-in --frigate F03 --output "{out_path}"')
        os.system(f'python "{CUSTOS}" --mode gate --gate 3 --decision yes --notes "{ready} warriors ready"')

    print("[F03 FORGEWARD --finalize] Gate 3 passée — passer à F04 HERALD")


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
    parser = argparse.ArgumentParser(description="F03 FORGEWARD")
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
