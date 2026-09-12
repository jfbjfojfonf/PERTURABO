"""
F02 BREACHER — Scoring + 20 angles d'attaque
Usage:
  python breacher.py --prepare  → assemble raw_intel + rules → iron_prompt.txt
  python breacher.py --iron     → call_oracle → breacher_output.json
  python breacher.py --finalize → valide JSON, check-in IW_CUSTOS, Gate 2
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
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


# ─── Scoring ──────────────────────────────────────────────────────────────────

WEIGHTS = {
    "popularite": 0.35,
    "latence": 0.25,
    "wrappers_github": 0.20,
    "frustration_pricing": 0.20,
}

ANGLE_TYPES = [
    "tier_agressif_2usd",
    "tier_agressif_5usd",
    "tier_freemium",
    "endpoint_focus_email",
    "endpoint_focus_profile",
    "endpoint_focus_company",
    "endpoint_focus_bulk",
    "endpoint_focus_search",
    "format_json_csv",
    "format_json_resume",
    "niche_ecommerce",
    "niche_recrutement",
    "niche_sales",
    "niche_marketing",
    "async_ultrarapide",
    "version_simplifiee",
    "version_enrichie",
    "combinaison_endpoints",
    "specialisation_pays_fr",
    "specialisation_pays_us",
]


def score_target(intel: dict) -> dict:
    """Score une cible à partir des données brutes."""
    score = 0.0
    details = {}

    # Popularité (0–100 → normalize)
    rapid_listings = intel.get("rapid_listings", [])
    pop_score = min(len(rapid_listings) * 5, 100)
    score += pop_score * WEIGHTS["popularite"]
    details["popularite"] = pop_score

    # Latence (plus c'est lent, plus c'est une opportunité)
    lat = intel.get("best_latency_ms", 0)
    if lat == 0:
        lat_score = 30  # inconnu = opportunité modérée
    elif lat > 5000:
        lat_score = 100
    elif lat > 2000:
        lat_score = 70
    elif lat > 500:
        lat_score = 40
    else:
        lat_score = 10
    score += lat_score * WEIGHTS["latence"]
    details["latence"] = lat_score

    # Wrappers GitHub
    gh_data = intel.get("github_wrappers", [])
    total_wrappers = sum(g.get("total_wrappers", 0) for g in gh_data)
    wrap_score = min(total_wrappers * 2, 100)
    score += wrap_score * WEIGHTS["wrappers_github"]
    details["wrappers_github"] = wrap_score

    # Frustration pricing (présence de reviews négatives ou de prix élevés)
    frustration = intel.get("frustration_pricing_signal", 50)
    score += frustration * WEIGHTS["frustration_pricing"]
    details["frustration_pricing"] = frustration

    return {"score": round(score, 1), "details": details}


# ─── Angles d'attaque ─────────────────────────────────────────────────────────

def build_angles(scoring: dict, intel: dict) -> list[dict]:
    """Génère les 20 angles d'attaque à partir du scoring et de l'intel."""
    angles = []
    for i, angle_type in enumerate(ANGLE_TYPES):
        angles.append({
            "id": i + 1,
            "type": angle_type,
            "description": f"Variante {i + 1} : {angle_type.replace('_', ' ')}",
            "target_endpoint": intel.get("target_endpoint", "/api/v1/search"),
            "suggested_price": _suggest_price(angle_type),
        })
    return angles


def _suggest_price(angle_type: str) -> str:
    if "2usd" in angle_type:
        return "$2/month (10k req)"
    if "5usd" in angle_type:
        return "$5/month (50k req)"
    if "freemium" in angle_type:
        return "Free tier + $9/month"
    return "$4/month (25k req)"


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_prepare():
    liber_path = MONDE_ROOT / "liber_api.json"
    if not liber_path.exists():
        print("[F02] ERREUR : liber_api.json introuvable")
        sys.exit(1)

    with open(liber_path) as f:
        liber = json.load(f)

    siege_id = liber.get("siege_id", "API-001")
    intel_path = ARCHIVUM / "targets" / siege_id / "raw_intel.json"

    if not intel_path.exists():
        # Essai dans F01/OUT
        intel_path = MONDE_ROOT / "fregates" / "F01_SENTINEL" / "OUT" / "raw_intel.json"

    if not intel_path.exists():
        print(f"[F02] ERREUR : raw_intel.json introuvable — F01 SENTINEL doit tourner d'abord")
        sys.exit(1)

    with open(intel_path) as f:
        raw_intel = json.load(f)

    # Charger rules couche froide
    rules_context = _load_rules()

    # Charger system_prompt et contrat
    system_prompt = (CONTRACTS / "system_prompt.md").read_text() if (CONTRACTS / "system_prompt.md").exists() else ""
    iron_contract = (CONTRACTS / "iron_prompt.md").read_text() if (CONTRACTS / "iron_prompt.md").exists() else ""
    checklist = {}
    checklist_path = CONTRACTS / "api_scoring_checklist.json"
    if checklist_path.exists():
        with open(checklist_path) as f:
            checklist = json.load(f)

    iron_prompt = f"""{system_prompt}

---

{iron_contract}

---

## DONNÉES BRUTES F01 SENTINEL

{json.dumps(raw_intel, indent=2, ensure_ascii=False)[:8000]}

---

## RÈGLES ARCHIVUM (couche froide)

{rules_context}

---

## GRILLE DE SCORING

{json.dumps(checklist, indent=2, ensure_ascii=False)}

---

## MISSION F02 BREACHER

Tu es F02 BREACHER. Tu dois :
1. Identifier la meilleure cible API à assiéger dans les données ci-dessus
2. Calculer son score selon les 4 dimensions (popularité × 0.35, latence × 0.25, wrappers × 0.20, frustration_pricing × 0.20)
3. Identifier 20 angles d'attaque distincts (prix, endpoint, niche, format, vitesse)
4. Identifier la faille principale (latence élevée ? pricing excessif ? endpoint manquant ?)

Réponds UNIQUEMENT avec un JSON valide, sans texte avant ni après :
{{
  "cible_nom": "...",
  "cible_host": "....p.rapidapi.com",
  "cible_categorie": "...",
  "score": 0-100,
  "score_details": {{
    "popularite": 0-100,
    "latence": 0-100,
    "wrappers_github": 0-100,
    "frustration_pricing": 0-100
  }},
  "faille_principale": "...",
  "latence_estimee_ms": 0,
  "prix_leader": "$X/month",
  "wrappers_actifs": 0,
  "angles_attaque": [
    {{"id": 1, "type": "...", "description": "...", "prix_suggere": "..."}}
  ]
}}
"""

    prompt_path = IN_DIR / "iron_prompt.txt"
    prompt_path.write_text(iron_prompt, encoding="utf-8")
    print(f"[F02 BREACHER --prepare] iron_prompt.txt prêt ({len(iron_prompt)} chars)")
    print(f"  → {prompt_path}")


def cmd_iron():
    prompt_path = IN_DIR / "iron_prompt.txt"
    if not prompt_path.exists():
        print("[F02] ERREUR : iron_prompt.txt manquant — lance --prepare d'abord")
        sys.exit(1)

    prompt = prompt_path.read_text(encoding="utf-8")

    try:
        from ai_gateway import call_oracle
    except ImportError:
        print("[F02] ERREUR : impossible d'importer ai_gateway depuis CORE/")
        sys.exit(1)

    print("[F02 BREACHER --iron] Appel Oracle (F02)...")
    raw = call_oracle("F02", prompt)

    # Extraire le JSON de la réponse
    output = _extract_json(raw)
    if not output:
        print(f"[F02] ERREUR : réponse Oracle non parsable")
        print(f"Réponse brute : {raw[:500]}")
        sys.exit(1)

    out_path = OUT_DIR / "breacher_output.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"[F02 BREACHER --iron] breacher_output.json produit")
    print(f"  Cible : {output.get('cible_nom')} — Score : {output.get('score')}/100")
    print(f"  Faille : {output.get('faille_principale')}")
    print(f"  → {out_path}")


def cmd_finalize():
    out_path = OUT_DIR / "breacher_output.json"
    if not out_path.exists():
        print("[F02] ERREUR : breacher_output.json manquant — lance --iron d'abord")
        sys.exit(1)

    with open(out_path) as f:
        output = json.load(f)

    # Validation schéma minimal
    required = ["cible_nom", "score", "faille_principale", "angles_attaque"]
    missing = [k for k in required if k not in output]
    if missing:
        print(f"[F02] ERREUR : champs manquants dans breacher_output.json : {missing}")
        sys.exit(1)

    angles_count = len(output.get("angles_attaque", []))
    if angles_count < 10:
        print(f"[F02] AVERTISSEMENT : seulement {angles_count} angles (20 recommandés)")

    print("\n" + "=" * 60)
    print("  GATE 2 — FICHE BREACHER")
    print("=" * 60)
    print(f"  Cible       : {output.get('cible_nom')}")
    print(f"  Score       : {output.get('score')}/100")
    print(f"  Faille      : {output.get('faille_principale')}")
    print(f"  Latence     : {output.get('latence_estimee_ms', '?')} ms")
    print(f"  Prix leader : {output.get('prix_leader', '?')}")
    print(f"  Wrappers GH : {output.get('wrappers_actifs', '?')}")
    print(f"  Angles      : {angles_count} Iron Warriors prêts")
    print("=" * 60)

    for i, angle in enumerate(output.get("angles_attaque", [])[:20], 1):
        print(f"  [{i:02d}] {angle.get('type')} — {angle.get('prix_suggere', '')}")

    print("=" * 60)
    decision = input("\n  WARSMITH — Valider la cible ? (oui/non) : ").strip().lower()

    if CUSTOS.exists():
        os.system(f'python "{CUSTOS}" --mode check-in --frigate F02 --output "{out_path}"')
        if decision in ("oui", "o", "yes", "y"):
            os.system(f'python "{CUSTOS}" --mode gate --gate 2 --decision yes --notes "{output.get("cible_nom")}"')
            print("[F02 BREACHER --finalize] Gate 2 validée — passer à F03 FORGEWARD")
        else:
            os.system(f'python "{CUSTOS}" --mode gate --gate 2 --decision no --notes "rejet warsmith"')
            print("[F02 BREACHER --finalize] Gate 2 refusée — relancer TYRANT + SENTINEL")
    else:
        print(f"[F02] IW_CUSTOS.py introuvable")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _load_rules() -> str:
    rules_dir = ARCHIVUM / "rules"
    if not rules_dir.exists():
        return "(aucune règle archivum disponible)"
    rules = []
    for f in sorted(rules_dir.glob("*.md"))[:5]:
        rules.append(f"### {f.stem}\n{f.read_text(encoding='utf-8', errors='replace')[:1000]}")
    return "\n\n".join(rules) if rules else "(couche froide vide)"


def _extract_json(text: str) -> dict | None:
    import re
    # Chercher bloc JSON dans la réponse
    match = re.search(r'\{[\s\S]*\}', text)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="F02 BREACHER")
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
