#!/usr/bin/env python3
"""
campaign_gate — Le Garde de Fer des campagnes (branche v2-live).

Résout quelle campagne autorise une chaîne Twitch, vérifie le cycle,
et décide du mode de session. Le Warsmith ne mélange JAMAIS le soumissible
et le test technique.

Sources :
  - ARCHIVUM/campaign/live_campaigns.json  (registry : chaîne → campagne)
  - Le cycle et les règles détaillées restent dans la directive référencée.

Fonctions :
  - load_registry()          : lit la registry (tolérant aux pannes → registry vide)
  - resolve_channels(list)   : chaîne → {campaign_id, campaign_state, eligible, reason}
  - session_mode(res)        : 'campaign' | 'technical_test' | 'mixed'
  - campaign_fields(ch, res) : champs à coller sur chaque verdict du gate

Hérésies interdites :
❌ Aucune dépendance pip (stdlib uniquement)
❌ Jamais bloquer une session pour une registry absente/corrompue (→ technical_test)
"""

import json
from datetime import date
from pathlib import Path

# Registry = 4 niveaux au-dessus du CODEBASE : libs[0] → CODEBASE[1] → F00B_VOX[2]
# → F00_IRON_SENTINEL[3] → CLIPPING[4] → ARCHIVUM/campaign/
_REGISTRY = (Path(__file__).resolve().parents[4]
             / "ARCHIVUM" / "campaign" / "live_campaigns.json")

# États possibles d'une campagne par rapport à aujourd'hui
STATE_ACTIVE = "active"
STATE_EXPIRED = "expired_cycle"
STATE_NOT_STARTED = "not_started"


def load_registry():
    """Lit la registry. Absente ou corrompue → registry vide (jamais de crash)."""
    try:
        with open(_REGISTRY, "r", encoding="utf-8") as f:
            data = json.load(f)
        campaigns = data.get("campaigns", [])
        if isinstance(campaigns, list):
            return campaigns
        return []
    except Exception:  # noqa: BLE001 — tolérance totale
        return []


def _cycle_state(cycle, today=None):
    """Compare un cycle {start, end} (ISO date) à la date du jour."""
    if not isinstance(cycle, dict):
        return STATE_ACTIVE  # pas de cycle déclaré = pas de restriction
    today = today or date.today()
    try:
        start = date.fromisoformat(str(cycle.get("start", ""))[:10])
        end = date.fromisoformat(str(cycle.get("end", ""))[:10])
    except ValueError:
        return STATE_ACTIVE
    if today < start:
        return STATE_NOT_STARTED
    if today > end:
        return STATE_EXPIRED
    return STATE_ACTIVE


def resolve_channels(channels, today=None):
    """
    Pour chaque chaîne : à quelle campagne elle appartient, et l'état du cycle.
    Retourne dict : login → {campaign_id|None, creator, campaign_state, eligible, reason}
      - eligible=True  : campagne active couvrant ce cycle → soumissible
      - eligible=False : hors campagne, cycle expiré ou pas commencé
    Plusieurs campagnes sur une même chaîne : la première ACTIVE gagne,
    sinon la première tout court (avec warning dans la reason).
    """
    registry = load_registry()
    result = {}
    for ch in channels:
        key = (ch or "").strip().lower()
        matches = []
        for camp in registry:
            chans = [c.strip().lower() for c in camp.get("twitch_channels", [])]
            if key in chans:
                matches.append(camp)
        if not matches:
            result[ch] = {
                "campaign_id": None,
                "creator": None,
                "campaign_state": None,
                "eligible": False,
                "reason": "hors campagne — session technique, non soumissible",
            }
            continue
        # priorité : campagne active d'abord
        ranked = sorted(matches, key=lambda m: 0 if _cycle_state(
            m.get("cycle"), today) == STATE_ACTIVE else 1)
        camp = ranked[0]
        state = _cycle_state(camp.get("cycle"), today)
        note = ""
        if len(matches) > 1:
            note = f" (+{len(matches) - 1} autre(s) campagne(s) sur cette chaîne)"
        eligible = (state == STATE_ACTIVE)
        reason = {
            STATE_ACTIVE: f"campagne {camp.get('campaign_id')} ACTIVE",
            STATE_EXPIRED: f"cycle expiré (fin {camp.get('cycle', {}).get('end')}) — non soumissible",
            STATE_NOT_STARTED: f"cycle pas encore commencé (début {camp.get('cycle', {}).get('start')})",
        }[state] + note
        result[ch] = {
            "campaign_id": camp.get("campaign_id"),
            "creator": camp.get("creator_name"),
            "campaign_state": state,
            "eligible": eligible,
            "reason": reason,
        }
    return result


def session_mode(resolved):
    """
    Décide le mode de la session à partir du resolve_channels().
      - 'campaign'       : toutes les chaînes sont éligibles (soumissible)
      - 'technical_test' : aucune chaîne éligible
      - 'mixed'          : mélange interdit → la session doit être refusée
    """
    eligibles = [r["eligible"] for r in resolved.values()]
    if all(eligibles):
        return "campaign"
    if not any(eligibles):
        return "technical_test"
    return "mixed"


def campaign_fields(channel, resolved):
    """Champs à coller sur un verdict du gate (propagés vers artefacts + board)."""
    r = resolved.get(channel, {})
    return {
        "campaign_eligible": bool(r.get("eligible")),
        "campaign_id": r.get("campaign_id"),
        "campaign_state": r.get("campaign_state"),
    }
