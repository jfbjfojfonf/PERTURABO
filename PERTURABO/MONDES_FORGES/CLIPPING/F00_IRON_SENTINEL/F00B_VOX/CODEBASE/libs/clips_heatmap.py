"""
clips_heatmap.py — Capteur clips communautaires (heatmap) — P2 phase 3
======================================================================
La communauté a déjà voté : les clips Twitch sont le signal de viralité le plus
proche d'un dataset étiqueté. Ce capteur reconstruit une heatmap densité × vues
sur la timeline de la VOD cible.

Approche SANS clé : endpoint GraphQL public de Twitch (celui du front web),
via le Client-ID web anonyme déjà utilisé par `fetch_chat_replay`. Aucun compte,
aucune auth, aucun secret.

Génère pour chaque clip aligné sur la VOD : {offset (s), vues, titre}.
  - `density` = nb de clips ≠ créateurs sur une fenêtre  → consensus.
  - `views`   = vues cumulées                             → preuve de performance.
  - `title`  = hook déjà écrit par la commu               → référence pour F04.

⚠️  Usage interne Twitch (zone grise, fragile) : dégradation gracieuse systématique.
Jamais de spam — lecture d'une seule page (≤100 clips) par run.
"""

import json
import urllib.request

CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"
GQL_URL = "https://gql.twitch.tv/gql"

QUERY = """query ClipsCard($login:String!,$first:Int!){
 user(login:$login){
  clips(first:$first){
   edges{ node{ slug title viewCount videoOffsetSeconds video{ id } } }
  }
 }
}"""


def fetch_channel_clips(login, vod_id, limit=100):
    """Retourne [{offset, views, title}] pour la VOD cible. [] si aucun/erreur."""
    if not login or not vod_id:
        return []
    req = urllib.request.Request(
        GQL_URL, method="POST",
        data=json.dumps({"operationName": "ClipsCard",
                         "variables": {"login": login, "first": int(limit)},
                         "query": QUERY}).encode("utf-8"),
        headers={"Client-ID": CLIENT_ID, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return []
    edges = ((data.get("data") or {}).get("user") or {}).get("clips", {}).get("edges") or []
    out = []
    for e in edges:
        n = e.get("node") or {}
        vid = (n.get("video") or {}).get("id")
        off = n.get("videoOffsetSeconds")
        if str(vid) != str(vod_id) or off is None:
            continue  # clip d'une autre VOD, ou position inconnue
        out.append({
            "offset": float(off),
            "views": int(n.get("viewCount") or 0),
            "title": (n.get("title") or "").strip(),
        })
    return out


def clips_signal(clips, s, e):
    """{density, views, titles} des clips dans [s,e). None si clips vide."""
    if not clips:
        return None
    inside = [c for c in clips if float(s) <= float(c["offset"]) < float(e)]
    return {
        "density": len(inside),
        "views": sum(int(c["views"]) for c in inside),
        "titles": [c["title"] for c in inside],
    }
