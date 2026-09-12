# 🏰 SALLE DE GUERRE — Le Prince Voit Tout

> Doctrine : « Le Primarque voit tous les points d'intérêt depuis son siège —
> ce qui lui garantit une victoire totale. » (plan : `PLAN_SALLE_DE_GUERRE.md`
> dans PERTURABO, section 4 pour le contrat)

Ce dossier est le **récepteur de référence** du webhook F00C_VOX (Livraison B) :
il reçoit les analyses (heatmap, barre rouge Most Replayed, candidats), vérifie
le token partagé et les rend disponibles pour le dashboard `/war-room`.

## Le contrat (résumé)

| Champ | Contenu |
|---|---|
| `run_id` | Identifiant unique du run (idempotence) |
| `siege_id` | Campagne / référence source |
| `mode` | `vod` (tout d'un coup) ou `live` (au fil de l'eau) |
| `status` | `full` / `metadata_only` / `metadata_only_media_error` |
| `source` | Plateforme, type, id, référence |
| `heatmap` | Buckets d'attention F00C (`start_sec`, `end_sec`, `attention`, `attention_norm`) |
| `replayed_curve` | Barre rouge YouTube (comportement humain réel) + `replayed_note` si absente |
| `fused_heatmap` | Fusion pondérée capteur × comportement (0.6 / 0.4) |
| `candidates` | Segments candidats (schéma canonique PUR) |
| `pushed_at` | Horodatage ISO |

Auth : en-tête **`X-Siege-Token`** (secret partagé `SIEGE_WEBHOOK_TOKEN`).
Un payload invalide est rejeté en 422 — jamais de silence.

## Usage

```bash
# Self-test hors-ligne (round-trip complet, aucun serveur)
python3 war_room/receiver.py --self-test

# Tests
python3 -m pytest war_room/tests/ -q

# Démo reproductible (remplit le dashboard sans attendre le run GitHub)
python3 war_room/seed_demo.py

# Serveur (accepte les POST de F00C, sert le dashboard + GET /api/war-room)
SIEGE_WEBHOOK_TOKEN=mon-secret python3 war_room/receiver.py
# Port : --port N, sinon env PORT, sinon 8787
```

## Endpoints (Livraisons C et D livrées)

| Route | Méthode | Rôle |
|---|---|---|
| `/` | GET | **Dashboard Salle de Guerre** (`docs/war_room.html`) |
| `/api/war-room` | GET | JSON complet — polling du dashboard (2 s en LIVE) |
| `/api/gate` | POST | Verdict Warsmith `{run_id, candidate_id, verdict: approved\|rejected}` |
| `/` | POST | Webhook F00C (payload complet, `X-Siege-Token` requis si configuré) |

**La boucle de retour Livraison D est fermée** : le dashboard poste les
verdicts sur `/api/gate`, le récepteur les stocke dans `war_room.json`
(`gates`, idempotents — re-voter la même chose ne gonfle pas les compteurs,
une inversion remplace proprement le compteur précédent), et le pipeline
PERTURABO relit `GET /api/war-room` pour connaître les clips GO.

## Le dashboard (docs/war_room.html)

- **Timeline SVG** : heatmap capteur (or) + barre rouge Most Replayed (rouge
  pointillé) + fusion 0.6/0.4 (or vif) + blocs verts des candidats
- **Cartes candidats** triées par score avec boutons **GO / NO-GO** (gate)
- **Mode LIVE** : badge pulsé, nouveaux candidats marqués `NEW`, polling continu
- **Toggle DONNÉES BRUTES** : le JSON réel, rien que le JSON réel — doctrine
  « le Primarque voit tout », sans fard

## Côté F00C (PERTURABO) — envoi

```bash
python3 f00c_vox.py "https://www.youtube.com/watch?v=<ID>" \
  --fetch-replayed --to-candidats \
  --webhook-url https://<salle-de-guerre>/hook \
  # token : env SIEGE_WEBHOOK_TOKEN (jamais en ligne de commande dans les logs)
```

Côté GitHub Actions : input `webhook_url` + secret `SIEGE_WEBHOOK_TOKEN`.

## Données exposées

`docs/data/war_room.json` — dernier run + historique des runs + verdicts de
gate. C'est la source du dashboard `/war-room` et de la boucle de retour PERTURABO.
Le dépôt embarque un **seed démo Sophie Rain** (`war_room/seed_demo.py`) :
3 candidats, heatmap 100 buckets, barre rouge — l'état affiché tant que le
run réel n'a pas poussé.

## Sécurité

- Le token ne vit que dans les secrets (GitHub / environnement) — jamais dans
  un commit, un log ou le chat.
- Aucun fichier média ne transite : uniquement des données d'analyse (JSON).
