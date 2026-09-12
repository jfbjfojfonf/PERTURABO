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

# Serveur (accepte les POST de F00C, sert GET /api/war-room)
SIEGE_WEBHOOK_TOKEN=mon-secret python3 war_room/receiver.py --port 8787
```

## Côté F00C (PERTURABO) — envoi

```bash
python3 f00c_vox.py "https://www.youtube.com/watch?v=<ID>" \
  --fetch-replayed --to-candidats \
  --webhook-url https://<salle-de-guerre>/hook \
  # token : env SIEGE_WEBHOOK_TOKEN (jamais en ligne de commande dans les logs)
```

Côté GitHub Actions : input `webhook_url` + secret `SIEGE_WEBHOOK_TOKEN`.

## Données exposées

`docs/data/war_room.json` — dernier run + historique des runs. C'est la source
que lira le dashboard `/war-room` (Livraisons C et D) : timeline heatmap +
barre rouge + candidats, toggle DONNÉES BRUTES, gate GO/NO-GO.

## Sécurité

- Le token ne vit que dans les secrets (GitHub / environnement) — jamais dans
  un commit, un log ou le chat.
- Aucun fichier média ne transite : uniquement des données d'analyse (JSON).
