"""
vox_premium.py — P5 : arbitrage premium (clé NVIDIA / kimi-k3)
================================================================
N'analyse QUE les finalistes (les survivants des étages 0-2). Deux rôles :
  1. Score sémantique "potentiel de reframing" (hooks_pur.json) 0..10.
  2. Verdict final : relit chaque top_words + intensité → ok / weak / skip.

Dégradation gracieuse : sans clé / sans réseau, renvoie un score neutre
(5.0) pour ne jamais bloquer le pipeline. NE lit jamais la valeur de la clé
(elle vient de l'environnement côté serveur).
"""

import json
import os
import urllib.request

DEFAULT_BASE = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "moonshotai/kimi-k3"

_SYSTEM = (
    "Tu es l'arbitre viral de PERTURABO (mode PUR). Pour chaque extrait de "
    "transcript de stream, juge si le moment a un POTENTIEL DE REFRAMING : "
    "peut-il être transformé en histoire virale (sérieux→drôle, drôle→épique, "
    "neutre→dramatique, neutre→inspirant, personnel→universel) ? "
    "Réponds UNIQUEMENT en JSON : {\"score\": <0..10>, \"transformation\": \"<type>\", "
    "\"reason\": \"<10 mots max>\"}"
)

def _env_key():
    return os.environ.get("NVIDIA_NIM_API_KEY") or os.environ.get("CLIPPING_F00B_API_KEY") or os.environ.get("AI_GATEWAY_API_KEY")

def _base_url():
    return os.environ.get("NVIDIA_NIM_BASE_URL") or os.environ.get("AI_GATEWAY_BASE_URL") or DEFAULT_BASE

def _model():
    return os.environ.get("NVIDIA_NIM_MODEL") or DEFAULT_MODEL

def score_reframing(top_words, intensity=0.5, timeout=25):
    """Retourne {score, transformation, reason, used_premium:bool}."""
    key = _env_key()
    if not key or not (top_words or "").strip():
        return {"score": 5.0, "transformation": None, "reason": "no premium/no text", "used_premium": False}
    text = (top_words or "").strip()[:1500]
    payload = {
        "model": _model(),
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"Extrait (intensité {intensity}): \"{text}\""},
        ],
        "temperature": 0.2,
        "max_tokens": 80,
    }
    req = urllib.request.Request(
        _base_url() + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        # extraire le JSON (parfois enveloppé)
        mm = re.search(r"\{.*\}", content, re.S)
        obj = json.loads(mm.group(0)) if mm else {}
        score = float(obj.get("score", 5.0))
        return {
            "score": round(max(0.0, min(10.0, score)), 2),
            "transformation": obj.get("transformation"),
            "reason": str(obj.get("reason", ""))[:120],
            "used_premium": True,
        }
    except Exception as e:
        return {"score": 5.0, "transformation": None, "reason": f"premium_error: {type(e).__name__}", "used_premium": False}


def arbitrate(finalists, words=None, trigger_words=None):
    """Enrichit chaque finaliste d'un verdict premium + un score reframing.
    Renvoie finalists triés par (reframing + intensité)."""
    out = []
    for c in finalists:
        tw = c.get("top_words") or ""
        intens = float(c.get("intensity", c.get("signal_intensity", 0.5)))
        r = score_reframing(tw, intens)
        c["premium"] = {
            "reframing_score": r["score"],
            "transformation": r["transformation"],
            "reason": r["reason"],
            "used_premium": r["used_premium"],
        }
        # verdict combiné : intensité réelle + reframing
        combo = 0.5 * intens * 10 + 0.5 * r["score"]
        if combo >= 6.5:
            verdict = "ok"
        elif combo >= 4.5:
            verdict = "weak"
        else:
            verdict = "skip"
        c["verdict"] = verdict
        c["verdict_score"] = round(combo, 2)
        out.append(c)
    out.sort(key=lambda x: (-x["verdict_score"], -(x.get("premium") or {}).get("reframing_score", 0)))
    return out
