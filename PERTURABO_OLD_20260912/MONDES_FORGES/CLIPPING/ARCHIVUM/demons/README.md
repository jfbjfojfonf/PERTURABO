# ARCHIVUM/demons/ — Clips qui dominent

> *Démon (campagne + veille). Cartographie par TYRANT prospectif.*
> *Lu par F02_TYRANT_CAMP pour identifier les océans bleus sur les campagnes futures.*

---

## Deux types de Démon ici

### 1. Démon de campaigne
Le clip de référence fourni par le Warsmith pour une campaigne spécifique. Stocké dans `ARCHIVUM/campaign/reference_clip.json` + `reference_skeleton.json`. **Pas dupliqué ici** — vit dans `campaign/`.

### 2. Démon de veille (ici, dans `demons/`)
Identifié par `TYRANT/` (mode prospectif) hors campaigne. Le scanner (F00_CAPTEURS) peut aussi contribuer via `demon_scanner.py`.

Ces Démon veille sont la mémoire globale du territoire clipping — utilisés par F02_TYRANT_CAMP pour identifier des océans bleus sur les prochaines campagnes.

---

## Structure d'un `<demon_id>.json`

```json
{
  "demon_id": "slug_unique",
  "demon_url": "...",
  "platform": "youtube|tiktok|instagram",
  "views": N,
  "outlier_score": <float>,    // > 3x = Démon
  "dominant_emotion": "drame|joie|outrage|inspiration|...",
  "dominant_engagement_type": "question|assertion|cliffhanger|...",
  "exploited_territories": ["drame"],
  "blue_ocean_unlocked": [
    {
      "territory": "grossophobie",
      "rationale": "...",
      "estimated_saturation": "low|medium|high",
      "blue_ocean_depth": 1
    }
  ],
  "skeleton_extract": {
    "hook_type": "...",
    "loop_technique": "...",
    "structure_narrative": "..."
  },
  "scanned_at": "<ISO8601>"
}
```

## Règle 1-couche

`blue_ocean_depth` est **TOUJOURS 1** dans cette ARCHIVUM. Le scanner TYRANT ne doit jamais proposer une profondeur 2 — cela serait hérésie (cf. `CONTRACTS/clipping_rules.md` et `TYRANT/CODEBASE/TRACKING.md`).

## À remplir

Ce dossier est nourri par `TYRANT prospectif` au runtime. À l'init, vide avec `.gitkeep`. Le Warsmith peut pré-peupler avec quelques Démon déjà connus s'il en a (optional — TYRANT les trouvera au scan).
