#!/usr/bin/env python3
"""
helix_clipper — La Main de VOX sur l'API Twitch Helix (branche v2-live).

100% stdlib (urllib). Nécessite :
  - TWITCH_TOKEN      : user access token avec scope clips:edit (+ modération)
  - TWITCH_CLIENT_ID  : client id de l'application Twitch

Fonctions :
  - is_token_ready()            : env présente ?
  - get_user_id(login)          : login → broadcaster_id
  - get_stream_info(login)      : live ? started_at ? viewers ? game ?
  - create_clip(broadcaster_id) : clip serveur capté IMMÉDIATEMENT (le live continue)

Hérésies interdites :
❌ Aucune dépendance pip
❌ Aucun token écrit dans un fichier (env uniquement)
"""

import json
import os
import urllib.error
import urllib.request

API = "https://api.twitch.tv/helix"


def _error_body(exc):
    """Extrait le corps d'une HTTPError Twitch (souvent la vraie raison)."""
    try:
        return exc.read().decode("utf-8", errors="replace")[:300]
    except Exception:  # noqa: BLE001
        return str(exc)


def _headers():
    return {
        "Authorization": f"Bearer {os.environ.get('TWITCH_TOKEN', '')}",
        "Client-Id": os.environ.get("TWITCH_CLIENT_ID", ""),
        "Content-Type": "application/json",
    }


def is_token_ready():
    return bool(os.environ.get("TWITCH_TOKEN")) and bool(os.environ.get("TWITCH_CLIENT_ID"))


def _get(path, params):
    url = f"{API}{path}?{params}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} — {_error_body(exc)}") from exc


def _post(path, params):
    url = f"{API}{path}?{params}"
    req = urllib.request.Request(url, headers=_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} — {_error_body(exc)}") from exc


def get_user_id(login):
    data = _get("/users", f"login={login}")
    users = data.get("data", [])
    return users[0]["id"] if users else None


def get_stream_info(login):
    data = _get("/streams", f"user_login={login}")
    streams = data.get("data", [])
    if not streams:
        return None
    s = streams[0]
    return {
        "login": s.get("user_login"),
        "broadcaster_id": s.get("user_id"),
        "is_live": s.get("type") == "live",
        "title": s.get("title"),
        "game": s.get("game_name"),
        "viewers": s.get("viewer_count"),
        "started_at": s.get("started_at"),  # ISO 8601 UTC
    }


def create_clip(broadcaster_id):
    """Capture un clip serveur MAINTENANT (30 dernières secondes du live)."""
    data = _post("/clips", f"broadcaster_id={broadcaster_id}&is_delayed=false")
    clips = data.get("data", [])
    if not clips:
        return None
    c = clips[0]
    return {
        "clip_id": c.get("id"),
        "edit_url": c.get("edit_url"),
        "url": f"https://clips.twitch.tv/{c.get('id')}",
    }
