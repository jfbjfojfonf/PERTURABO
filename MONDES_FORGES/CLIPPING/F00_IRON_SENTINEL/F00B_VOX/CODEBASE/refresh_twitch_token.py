#!/usr/bin/env python3
"""
refresh_twitch_token — Renouvelle le token Twitch à chaque run (branche v2-live).

Le token user généré via twitchtokengenerator vit ~4 h seulement. Ce script
échange le REFRESH TOKEN contre un token frais, AVANT que le radar/l'Oracle
ne tournent. 100% stdlib.

Entrées (env ou Secrets GitHub) :
  - TWITCH_REFRESH_TOKEN : le refresh token (longue durée)
  - TWITCH_CLIENT_ID     : l'identifiant de l'app
  - TWITCH_CLIENT_SECRET : le secret de l'app (requis par l'échange refresh_token)

Sortie :
  - écrit TWITCH_TOKEN dans $GITHUB_ENV pour les steps suivants du job
  - met à jour le refresh token si Twitch en renvoie un nouveau
  - mode --check : valide juste le token courant et sort (0 = OK, 1 = KO)

Hérésies interdites :
❌ Aucune dépendance pip
❌ Aucun token/secret affiché dans les logs (masqués)
"""

import json
import os
import sys
import urllib.request
import urllib.parse

TOKEN_URL = "https://id.twitch.tv/oauth2/token"


def _post_form(params):
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(TOKEN_URL, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()[:300]
        return {"error": f"HTTP {exc.code}", "detail": body}, exc.code


def validate(token):
    req = urllib.request.Request(
        "https://id.twitch.tv/oauth2/validate",
        headers={"Authorization": f"OAuth {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            info = json.loads(resp.read().decode())
    except urllib.error.HTTPError:
        return None
    return info


def append_github_env(line):
    env_file = os.environ.get("GITHUB_ENV")
    if env_file:
        with open(env_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    # Hors Actions (test local) : rien, les variables restent dans les logs masqués.


def main():
    client_id = os.environ.get("TWITCH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("TWITCH_CLIENT_SECRET", "").strip()
    refresh = os.environ.get("TWITCH_REFRESH_TOKEN", "").strip()
    current = os.environ.get("TWITCH_TOKEN", "").strip()

    # Mode --check : le token courant suffit-il ?
    if "--check" in sys.argv:
        if not current:
            print("❌ TWITCH_TOKEN absent")
            sys.exit(1)
        info = validate(current)
        if info is None:
            print("❌ TWITCH_TOKEN invalide ou expiré")
            sys.exit(1)
        left = info.get("expires_in", 0)
        scopes = info.get("scopes", [])
        ok = "clips:edit" in scopes
        print(f"✅ Token valide ({left}s restantes) — clips:edit : {'oui' if ok else 'NON'}")
        sys.exit(0 if ok else 1)

    if not (client_id and client_secret and refresh):
        print("❌ Il faut TWITCH_CLIENT_ID + TWITCH_CLIENT_SECRET + TWITCH_REFRESH_TOKEN")
        sys.exit(1)

    payload, status = _post_form({
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh,
    })
    if status != 200 or "access_token" not in payload:
        print(f"❌ Refresh échoué : {payload.get('error')} — {payload.get('detail', '')}")
        # Fallback : le token statique est-il encore valide ?
        if current:
            info = validate(current)
            if info:
                print(f"⚠️ Refresh impossible — token statique encore valide "
                      f"({info.get('expires_in')}s restantes). La session continue avec.")
                sys.exit(0)
            print("⚠️ Refresh impossible et token statique expiré —")
            print("   la session peut quand même tourner en timestamps seuls (sans clip Helix).")
        sys.exit(1)

    new_token = payload["access_token"]
    new_refresh = payload.get("refresh_token", refresh)
    expires_in = payload.get("expires_in", 0)

    append_github_env(f"TWITCH_TOKEN={new_token}")
    if new_refresh != refresh:
        append_github_env(f"TWITCH_REFRESH_TOKEN={new_refresh}")

    info = validate(new_token) or {}
    print(f"✅ Token rafraîchi — expire dans {expires_in}s "
          f"(compte : {info.get('login', '?')}, clips:edit : "
          f"{'oui' if 'clips:edit' in info.get('scopes', []) else 'NON'})")


if __name__ == "__main__":
    main()
