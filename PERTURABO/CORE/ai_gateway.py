"""
ai_gateway.py — Routeur Oracle PERTURABO
=========================================
Partagé entre tous les Mondes-Forges. Placé dans CORE/.
Toutes les frégates qui font des appels IA passent par ce module.
Jamais d'appel direct à l'API dans les frégates.

Variables d'environnement requises (dans .env ou environnement):
    AI_GATEWAY_BASE_URL  — ex: https://gateway.happycapy.ai
    AI_GATEWAY_API_KEY   — clé d'accès

Import depuis une frégate (chemin relatif CORE/):
    import sys, os
    _CORE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'CORE')
    sys.path.insert(0, os.path.abspath(_CORE))
    from ai_gateway import call_oracle, call_oracle_batch
"""

import os
import json
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

try:
    from openai import OpenAI
except ImportError:
    raise ImportError(
        "Package 'openai' requis: pip install openai>=1.0.0\n"
        "Ou: pip install -r CORE/requirements.txt"
    )

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optionnel si variables déjà dans l'env

# ─────────────────────────────────────────────
# Routing des modèles par frégate
# Chaque Monde-Forge peut passer son propre model_map
# Ces defaults sont calibrés pour le Monde-Forge API
# ─────────────────────────────────────────────
DEFAULT_MODEL_MAP = {
    "TYRANT":   "anthropic/claude-sonnet-4.6",   # Analyse stratégique — raisonnement
    "F01":      "anthropic/claude-haiku-4.5",    # Structurer données scrapées — rapide
    "F02":      "deepseek/deepseek-v4-flash",    # Scoring + angles — analytique + économique
    "F03":      "anthropic/claude-sonnet-4.6",   # Génération code FastAPI — qualité
    "F04":      "google/gemini-3.5-flash",       # Listings + READMEs — volume + vitesse
    "F05":      "anthropic/claude-sonnet-4.6",   # Blue ocean + validation — raisonnement
    "F06":      "anthropic/claude-haiku-4.5",    # Monitoring + alertes — rapide
    "CAPTEURS": "anthropic/claude-haiku-4.5",
    "DEFAULT":  "anthropic/claude-sonnet-4.6",
}

# Max tokens par frégate
# F03 génère 20 × api.py complets — besoin de contexte large
MAX_TOKENS_MAP = {
    "F03":    8192,
    "F04":    4096,
    "TYRANT": 4096,
    "DEFAULT": 4096,
}

# Temperature par frégate
# F03 génère du code — temperature basse pour la cohérence
TEMPERATURE_MAP = {
    "F03": 0.1,   # Code — déterministe
    "F04": 0.4,   # Texte marketing — un peu de créativité
    "DEFAULT": 0.2,
}


# ─────────────────────────────────────────────
# Client OpenAI (compatible OpenRouter / AI Gateway)
# ─────────────────────────────────────────────
def _get_client() -> OpenAI:
    base_url = os.environ.get("AI_GATEWAY_BASE_URL", "").rstrip("/")
    api_key  = os.environ.get("AI_GATEWAY_API_KEY", "")
    if not base_url or not api_key:
        raise EnvironmentError(
            "Variables d'environnement manquantes:\n"
            "  AI_GATEWAY_BASE_URL=https://...\n"
            "  AI_GATEWAY_API_KEY=sk-...\n"
            "Ajoute-les dans .env à la racine du Monde-Forge."
        )
    return OpenAI(base_url=f"{base_url}/api/v1", api_key=api_key)


def get_model(frigate_id: str, model_map: dict = None) -> str:
    """Retourne le modèle assigné à une frégate."""
    m = model_map or DEFAULT_MODEL_MAP
    return m.get(frigate_id, m.get("DEFAULT", "anthropic/claude-sonnet-4.6"))


# ─────────────────────────────────────────────
# Parsing du JSON depuis une réponse brute
# ─────────────────────────────────────────────
def _extract_json(raw: str) -> dict:
    """
    Tente d'extraire un objet JSON depuis une réponse brute.
    Gère les cas : JSON pur, ```json...```, ```...```, texte avant/après.
    """
    raw = raw.strip()

    # Cas 1 : JSON pur
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Cas 2 : bloc markdown ```json...``` ou ```...```
    if "```" in raw:
        import re
        # Cherche le contenu entre ``` ou ```json
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

    # Cas 3 : chercher la première { et la dernière } dans le texte
    start = raw.find("{")
    end   = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start:end+1])
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError("Impossible d'extraire un JSON valide", raw, 0)


# ─────────────────────────────────────────────
# call_oracle — appel unique
# ─────────────────────────────────────────────
def call_oracle(
    frigate_id: str,
    prompt: str,
    system_prompt: str = None,
    model: str = None,
    max_retries: int = 3,
    model_map: dict = None,
    expect_json: bool = True,
) -> dict:
    """
    Appel unique à l'Oracle.

    Args:
        frigate_id:    Identifiant de la frégate appelante (ex: "F02", "TYRANT")
        prompt:        Prompt utilisateur complet
        system_prompt: Prompt système (optionnel — si None, utilise le contrat de la frégate)
        model:         Override du modèle (optionnel)
        max_retries:   Nombre de tentatives si JSON invalide ou erreur API
        model_map:     Table de routing custom (optionnel)
        expect_json:   Si True, parse la réponse en JSON et retry si invalide

    Returns:
        {
          "status":   "ok" | "error",
          "content":  dict | str,          # dict si expect_json=True
          "model":    str,
          "attempts": int,
          "error":    str | None
        }
    """
    target_model = model or get_model(frigate_id, model_map)
    max_tokens   = MAX_TOKENS_MAP.get(frigate_id, MAX_TOKENS_MAP["DEFAULT"])
    temperature  = TEMPERATURE_MAP.get(frigate_id, TEMPERATURE_MAP["DEFAULT"])

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    client = _get_client()
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=target_model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            raw = response.choices[0].message.content

            if not expect_json:
                return {
                    "status":   "ok",
                    "content":  raw,
                    "model":    target_model,
                    "attempts": attempt,
                    "error":    None,
                }

            try:
                parsed = _extract_json(raw)
                return {
                    "status":   "ok",
                    "content":  parsed,
                    "model":    target_model,
                    "attempts": attempt,
                    "error":    None,
                }
            except json.JSONDecodeError as e:
                last_error = f"JSONDecodeError (attempt {attempt}/{max_retries}): {e}"
                if attempt < max_retries:
                    # Ajouter le contexte d'erreur pour le prochain essai
                    messages.append({"role": "assistant", "content": raw})
                    messages.append({
                        "role": "user",
                        "content": (
                            "Ta réponse précédente n'était pas du JSON valide. "
                            "Retourne UNIQUEMENT un objet JSON valide, sans texte avant ni après, "
                            "sans bloc markdown."
                        )
                    })
                    time.sleep(2 ** (attempt - 1))

        except Exception as e:
            last_error = f"APIError (attempt {attempt}/{max_retries}): {type(e).__name__}: {e}"
            if attempt < max_retries:
                time.sleep(2 ** (attempt - 1))

    return {
        "status":   "error",
        "content":  None,
        "model":    target_model,
        "attempts": max_retries,
        "error":    last_error,
    }


# ─────────────────────────────────────────────
# call_oracle_batch — appels parallèles
# Conçu pour F03 FORGEWARD : 20 Iron Warriors en simultané
# ─────────────────────────────────────────────
def call_oracle_batch(
    frigate_id: str,
    prompts: list,
    system_prompt: str = None,
    model: str = None,
    max_workers: int = 5,
    max_retries: int = 3,
    model_map: dict = None,
    expect_json: bool = True,
) -> list:
    """
    Appels parallèles à l'Oracle.
    Conçu pour F03 FORGEWARD qui génère 20 Iron Warriors simultanément.

    Args:
        prompts: liste de str OU liste de dict {"prompt": str, "system": str}
        max_workers: parallélisme (défaut 5 — évite le rate limiting)

    Returns:
        liste ordonnée (même ordre que prompts) de résultats call_oracle()
    """
    results = [None] * len(prompts)

    def _call_one(args):
        idx, p = args
        if isinstance(p, dict):
            prompt_text = p.get("prompt", "")
            sys_p       = p.get("system", system_prompt)
        else:
            prompt_text = p
            sys_p       = system_prompt
        result = call_oracle(
            frigate_id, prompt_text, sys_p,
            model, max_retries, model_map, expect_json
        )
        return idx, result

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_call_one, (i, p)): i for i, p in enumerate(prompts)}
        for future in as_completed(futures):
            try:
                idx, result = future.result()
                results[idx] = result
            except Exception as e:
                # Sécurité — ne jamais crasher le batch entier
                idx = futures[future]
                results[idx] = {
                    "status": "error", "content": None,
                    "model": "unknown", "attempts": 0,
                    "error": f"ThreadError: {e}"
                }

    return results


# ─────────────────────────────────────────────
# ping — test de connectivité
# ─────────────────────────────────────────────
def ping(model: str = None) -> dict:
    """
    Teste la connectivité avec l'AI Gateway.
    Utilisé dans le setup initial ou pour diagnostiquer une panne.

    Returns:
        {"status": "ok", "model": str, "latency_ms": float}
        {"status": "error", "error": str}
    """
    target = model or DEFAULT_MODEL_MAP["DEFAULT"]
    start = time.time()
    result = call_oracle(
        "DEFAULT",
        "Réponds uniquement: {"ping": "pong"}",
        model=target,
        max_retries=1,
        expect_json=True,
    )
    elapsed = (time.time() - start) * 1000

    if result["status"] == "ok":
        return {"status": "ok", "model": target, "latency_ms": round(elapsed, 1)}
    return {"status": "error", "error": result["error"]}


# ─────────────────────────────────────────────
# CLI — test direct depuis le terminal
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ai_gateway — test CLI")
    parser.add_argument("--ping", action="store_true", help="Tester la connectivité")
    parser.add_argument("--frigate", default="DEFAULT", help="ID de frégate (ex: F02)")
    parser.add_argument("--prompt", default=None, help="Prompt à envoyer")
    parser.add_argument("--no-json", action="store_true", help="Ne pas parser en JSON")
    args = parser.parse_args()

    if args.ping:
        result = ping()
        print(json.dumps(result, indent=2))
    elif args.prompt:
        result = call_oracle(
            args.frigate,
            args.prompt,
            expect_json=not args.no_json,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Test par défaut
        result = ping()
        print("Ping:", json.dumps(result, indent=2))
        print(f"\nModèles configurés:")
        for fid, m in DEFAULT_MODEL_MAP.items():
            print(f"  {fid:<12} → {m}")
