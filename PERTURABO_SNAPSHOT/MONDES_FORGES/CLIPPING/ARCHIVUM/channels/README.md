# ARCHIVUM/channels/ — Mes comptes de clipping

> *Un sous-dossier par compte. Tracke l'identité + la perf réel.*
> *Lu par F06_TRACKER (warmup check, perf update) et F04_COPYWRITER (contexte).*

---

## Structure attendue

```
channels/
├── <account_slug>/
│   ├── identity.json
│   └── performance.json
└── README.md  (ce fichier)
```

### `identity.json`

```json
{
  "account_slug": "monclipper_01",
  "platform": "tiktok|youtube|instagram",
  "market": "us_young_english",
  "niche": "...",
  "account_age_days": N,
  "warmup_status": "complete|incomplete",
  "warmup_started_at": "<ISO8601>",
  "warmup_completed_at": "<ISO8601 ou null>",
  "notes": "..."
}
```

Règle warmup : `warmup_status: "complete"` require `account_age_days >= 7` (voire 14 selon platform). Voir `CONTRACTS/clipping_rules.md` C5.

### `performance.json`

```json
{
  "account_slug": "monclipper_01",
  "packs_posted_count": N,
  "aggregate_views_24h": N,
  "aggregate_payout": N,
  "rejections_count": N,
  "last_post_at": "<ISO8601>",
  "by_campaign": [
    {
      "campaign_id": "...",
      "packs_count": N,
      "total_views": N,
      "total_payout": N
    }
  ]
}
```

Mis à jour par F06_TRACKER à chaque pack posté + à la fermeture de campagne.

## `youtube/` — Chaînes de contenu PERTURABO (hors tracking F06)

Depuis [DEV-ARCHIVUM-YOUTUBE], sous-dossier `youtube/` : copie locale des
chaînes de contenu du core `MONDES_FORGES/YOUTUBE/ARCHIVUM/channels/`
(the_stormist, golden_moment, built_by_sacrifice, threshold_lab —
identités + ADN + thumbnails + registry).

⚠️ **Ces chaînes ne sont PAS des comptes de clipping** : F06_TRACKER les
ignore (il ne lit que `channels/<slug>/` à la racine, pas `channels/youtube/`).
Elles servent de référence ADN/niche pour F04_COPYWRITER (reference_style)
et F02_TYRANT_CAMP (perception marché).

## À remplit par le Warsmith

- [ ] Créer un sous-dossier par compte de clipping
- [ ] Remplir `identity.json` pour chaque
- [ ] Laisser `performance.json` vide initialement — F06 le remplira au runtime
