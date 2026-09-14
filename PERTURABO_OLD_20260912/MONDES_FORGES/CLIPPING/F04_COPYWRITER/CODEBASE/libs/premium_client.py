"""
libs/premium_client.py — Phase B de F04_COPYWRITER
==================================================

Client du modèle premium — la frégate parle DIRECT au modèle premium,
sans IRON intermédiaire pour la génération.

Config : CONTRACTS/copywriter_secrets.json (gitignored, ne contient que
la référence env + le model_id). Fallback sur l'example public.

  {
    "env_var_name": "CLIPPING_PREMIUM_API_KEY",
    "model_id": "<model_premium_id>",
    "provider": "openai|openrouter|baseten|anthropic|other",
    "base_url": "...",           // si provider = "other"
    "max_tokens_per_call": 4096,
    "temperature_default": 0.7
  }

La clé réelle est lue depuis la variable d'env (jamais dans les fichiers).

Protocole OpenAI (chat/completions) : providers openai, openrouter, other.
Protocole Anthropic (messages) : provider anthropic.

Implémentation stdlib (urllib) — aucune dépendance SDK obligatoire,
compatible avec le poste faible du Warsmith.
"""

import json
import os
import urllib.error
import urllib.request

CONTRACTS_DIR = "CONTRACTS"
DEFAULT_ENV_VAR = "CLIPPING_PREMIUM_API_KEY"

BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "baseten": "https://inference.baseten.co/v1",
    "anthropic": "https://api.anthropic.com/v1",
}


class PremiumClientError(Exception):
    pass


class PremiumClient:
    def __init__(self, forge_root: str):
        self._forge_root = forge_root
        self._load_env_local()
        self.config = self._load_config()

    def _load_env_local(self):
        """Charge un .env.local (repo ou forge) si présent — stdlib, aucune
        dépendance. Les variables déjà présentes dans os.environ priment.
        (Freebuff injecte les clés API Keys via .env.local / env du workspace.)"""
        candidates = []
        base = self._forge_root
        for _ in range(4):  # forge_root, MONDES_FORGES, repo root, +1
            candidates.append(os.path.join(base, ".env.local"))
            base = os.path.dirname(base)
        seen = set()
        for path in candidates:
            if path in seen or not os.path.exists(path):
                continue
            seen.add(path)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#") or "=" not in line:
                            continue
                        key, _, val = line.partition("=")
                        key = key.strip()
                        val = val.strip().strip('"').strip("'")
                        if key and not os.environ.get(key):
                            os.environ[key] = val
            except OSError:
                continue

    # ------------------------------------------------------------------
    def _load_config(self) -> dict:
        secrets = os.path.join(self._forge_root, CONTRACTS_DIR, "copywriter_secrets.json")
        if os.path.exists(secrets):
            with open(secrets, "r", encoding="utf-8") as f:
                return json.load(f)
        example = os.path.join(self._forge_root, CONTRACTS_DIR,
                               "copywriter_secrets.example.json")
        if os.path.exists(example):
            with open(example, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _env_var_name(self) -> str:
        return self.config.get("env_var_name") or DEFAULT_ENV_VAR

    def _api_key(self) -> str:
        return os.environ.get(self._env_var_name(), "").strip()

    def _base_url(self) -> str:
        provider = self.config.get("provider", "other")
        return self.config.get("base_url") or BASE_URLS.get(provider, "")

    # ------------------------------------------------------------------
    def require_config(self):
        if not self._api_key():
            raise PremiumClientError(
                f"Clé premium absente — définir la var d'env '{self._env_var_name()}' "
                f"(config: CONTRACTS/copywriter_secrets.json)")
        if not self.config.get("model_id"):
            raise PremiumClientError(
                "model_id manquant dans copywriter_secrets.json "
                "(remplir par le Warsmith)")
        if not self._base_url():
            raise PremiumClientError(
                "base_url manquant (provider inconnu ou champ base_url absent)")

    def extract_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            return text.strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return text[start:end + 1]
        return text

    # ------------------------------------------------------------------
    def chat(self, system_prompt: str, user_prompt: str) -> str:
        self.require_config()
        provider = self.config.get("provider", "other")
        if provider == "anthropic":
            return self._chat_anthropic(system_prompt, user_prompt)
        return self._chat_openai_compatible(system_prompt, user_prompt)

    def _chat_openai_compatible(self, system_prompt: str, user_prompt: str) -> str:
        url = self._base_url().rstrip("/") + "/chat/completions"
        body = {
            "model": self.config["model_id"],
            "temperature": self.config.get("temperature_default", 0.7),
            "max_tokens": self.config.get("max_tokens_per_call", 4096),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if self.config.get("request_json_mode", False):
            body["response_format"] = {"type": "json_object"}
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "Authorization": f"Bearer {self._api_key()}",
            "Content-Type": "application/json",
            "User-Agent": "PERTURABO-F04-COPYWRITER",
        })
        response = self._fetch(req)
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as e:
            raise PremiumClientError(f"Réponse API non-JSON: {e}") from e
        try:
            return parsed["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise PremiumClientError(f"Structure réponse inattendue: {parsed}") from e

    def _chat_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        url = self._base_url().rstrip("/") + "/messages"
        body = {
            "model": self.config["model_id"],
            "max_tokens": self.config.get("max_tokens_per_call", 4096),
            "temperature": self.config.get("temperature_default", 0.7),
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "x-api-key": self._api_key(),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
            "User-Agent": "PERTURABO-F04-COPYWRITER",
        })
        response = self._fetch(req)
        try:
            parsed = json.loads(response)
            parts = parsed.get("content", [])
            return "".join(p.get("text", "") for p in parts)
        except (json.JSONDecodeError, AttributeError) as e:
            raise PremiumClientError(f"Réponse Anthropic invalide: {e}") from e

    def _fetch(self, req: urllib.request.Request) -> str:
        timeout = self.config.get("timeout_seconds", 240)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            snippet = e.read().decode("utf-8", errors="replace")[:500]
            raise PremiumClientError(
                f"HTTP {e.code} de {req.full_url}: {snippet}") from e
        except urllib.error.URLError as e:
            raise PremiumClientError(f"Réseau vers {req.full_url}: {e.reason}") from e
