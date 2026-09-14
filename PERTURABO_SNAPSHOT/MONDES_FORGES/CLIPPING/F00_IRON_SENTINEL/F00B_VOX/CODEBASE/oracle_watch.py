#!/usr/bin/env python3
"""
oracle_watch — L'Oracle de la branche v2-live.

Le radar ne dort pas 24h/24 : il ne se lève que quand ça vaut le coup.
Ce script (cron GitHub Actions toutes les 5 min, mode --once) :

  1. Interroge Helix : les chaînes surveillées sont-elles en LIVE ?
  2. Pour chaque live NOUVEAU (pas d'issue Oracle ouverte pour cette chaîne) :
       - crée une issue "[ORACLE][<channel>] LIVE — valider la session radar ?"
       - (option --auto-dispatch) déclenche directement le workflow radar
  3. Si la chaîne n'est plus en live → ferme l'issue Oracle correspondante.

100% stdlib (urllib). Le GITHUB_TOKEN et REPO sont fournis par le workflow :
  - env GITHUB_TOKEN : secret context github.token (pousse sur issues + actions)
  - env REPO         : "kioka8877-ux/PERTURABO"
  - env TWITCH_TOKEN + TWITCH_CLIENT_ID : pour Helix (sinon : rien détecté)

Hérésies interdites :
❌ Jamais deux issues Oracle ouvertes pour la même chaîne
❌ Jamais de déclenchement radar sans live réel confirmé
❌ Aucune dépendance pip
"""

import json
import os
import sys
import urllib.request

API = "https://api.github.com"
CODEBASE_DIR = __import__("pathlib").Path(__file__).resolve().parent
_LIBS_DIR = CODEBASE_DIR / "libs"
if _LIBS_DIR.exists():
    sys.path.insert(0, str(_LIBS_DIR))


def _gh(method, path, payload=None):
    token = os.environ.get("GITHUB_TOKEN", "")
    req = urllib.request.Request(
        f"{API}{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = resp.read().decode()
    return json.loads(body) if body else {}


def list_open_oracle_issues(repo, label="oracle-live"):
    """Issues ouvertes portant le label oracle-live."""
    data = _gh("GET", f"/repos/{repo}/issues?state=open&labels={label}&per_page=50")
    return {
        i["title"].split("]")[0].replace("[ORACLE][", "").strip(): i["number"]
        for i in data
        if i["title"].startswith("[ORACLE][")
    }


def create_oracle_issue(repo, channel, viewers, game):
    title = f"[ORACLE][{channel}] LIVE — valider la session radar ?"
    body = (
        f"📡 **{channel}** est en LIVE ({viewers} viewers, jeu : {game}).\n\n"
        f"**Pour lancer la session radar :**\n"
        f"Actions → `PERTURABO LIVE RADAR` → Run workflow → channel=`{channel}`\n\n"
        f"⚠️ Ne pas oublier : fermer cette issue une fois la session lancée/terminée.\n\n"
        f"_Oracle v2-live — détection automatique via Helix._"
    )
    return _gh(
        "POST",
        f"/repos/{repo}/issues",
        {"title": title, "body": body, "labels": ["oracle-live"]},
    ).get("number")


def close_oracle_issue(repo, number):
    _gh("PATCH", f"/repos/{repo}/issues/{number}", {"state": "closed"})


def dispatch_radar(repo, channels, duration_min):
    _gh(
        "POST",
        f"/repos/{repo}/actions/workflows/perturabo_live_radar.yml/dispatches",
        {
            "ref": "v2-live",
            "inputs": {
                "channels": ",".join(channels),
                "duration_min": str(duration_min),
            },
        },
    )


def main():
    repo = os.environ.get("REPO", "kioka8877-ux/PERTURABO")
    auto = "--auto-dispatch" in sys.argv

    input_file = CODEBASE_DIR.parent / "IN" / "oracle_input.json"
    channels, duration_min = [], 240
    if input_file.exists():
        with open(input_file, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        channels = cfg.get("twitch_channels", [])
        duration_min = cfg.get("session_duration_min", 240)
    if not channels:
        print("❌ Aucune chaîne à surveiller (IN/oracle_input.json).")
        sys.exit(1)

    try:
        import helix_clipper as hx
    except ImportError:
        print("❌ helix_clipper indisponible.")
        sys.exit(1)
    if not hx.is_token_ready():
        print("⚠️ TWITCH_TOKEN/TWITCH_CLIENT_ID absents — détection Helix impossible.")
        sys.exit(1)

    open_issues = list_open_oracle_issues(repo)
    print(f"🔍 Chaînes surveillées : {channels} | issues Oracle ouvertes : {open_issues}")

    live_channels = []
    for ch in channels:
        try:
            info = hx.get_stream_info(ch)
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ Helix fail ({ch}) : {exc}")
            continue
        if not info or not info.get("is_live"):
            if ch in open_issues:
                close_oracle_issue(repo, open_issues[ch])
                print(f"📴 {ch} hors-ligne — issue Oracle #{open_issues[ch]} fermée")
            continue

        live_channels.append(ch)
        if ch not in open_issues:
            num = create_oracle_issue(repo, ch, info["viewers"], info["game"])
            print(f"🔥 {ch} EN LIVE — issue Oracle #{num} créée")
            if auto:
                dispatch_radar(repo, [ch], duration_min)
                print(f"🚀 Radar déclenché automatiquement pour {ch}")
        else:
            print(f"⏳ {ch} déjà signalé (issue #{open_issues[ch]})")

    print(f"═══ Oracle : {len(live_channels)} live(s) en cours ═══")


if __name__ == "__main__":
    main()
