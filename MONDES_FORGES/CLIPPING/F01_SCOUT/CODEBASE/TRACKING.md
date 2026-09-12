# F01_SCOUT — TRACKING.md

> *"Le fer qui voit en premier. La forteresse n'est pénétrée qu'après avoir été vue."*
> *Frégate de reconnaissance. Jamais elle ne chasse hors des assets de la campagne — cela serait hérésie.*

---

## RÔLE

F01_SCOUT est la **frégate d'acquisition**. Elle prend en entrée les **assets fournis par la campagne** (URLs de vidéos longues, docs, briefs) et produit un `source_specimen.json` unifié consommé par F02_TYRANT_CAMP (Porte 1) et F03_SOURCE_HUNTER (Porte 3).

Elle **n'inventorie que ce que la campagne fournit**. Toute source non-issue des assets de la campagne est rejetée comme hérésie (cf. `CONTRACTS/clipping_rules.md` règle de strict-source).

---

## INPUTS

| Input | Source | Format | Obligatoire |
|---|---|---|---|
| `directive.md` (campaign goal doc) | Warsmith → `ARCHIVUM/campaign/directive.md` | Markdown | ✅ |
| `reference_clip_url` | Warsmith → `ARCHIVUM/campaign/reference_clip.json` (URL + métadonnées) | JSON | ✅ |
| `assets_urls[]` | Extrait de `directive.md` (section "assets" ou "sources fournies") | Liste d'URLs | ✅ |

Les assets peuvent être : vidéos YouTube longues, vidéos sponsor longues, archives de podcasts, streams Twitch, docs PDF (rare). Pas de récupération externe, jamais.

---

## OUTPUTS

### `OUT/source_specimen.json`

Format aligné sur le pattern specimen.json de `F01_SENTINEL` du core (YOUTUBE). Structure attendue :

```json
{
  "campaign_id": "...",
  "scanned_at": "<ISO8601>",
  "reference_clip": {
    "url": "...",
    "video_id": "...",
    "title": "...",
    "duration_sec": N,
    "view_count": N,
    "thumbnail": "...",
    "outlier_score": <float>,    // view_count / channel_shorts_baseline
    "platform": "youtube|tiktok|instagram",
    "metrics_extracted": {...}
  },
  "assets": [
    {
      "asset_id": "...",
      "url": "...",
      "type": "video_long|podcast|stream|doc",
      "duration_sec": N,
      "title": "...",
      "channel": "...",
      "transcript_available": true|false,
      "transcript_path": "ARCHIVUM/campaign/...",
      "thumbnail": "..."
    }
  ],
  "check_in_iw_custos": "<ISO8601>"
}
```

### Autres outputs
- `OUT/scout_report.md` — synthèse lisible par le Warsmith (résumé de la forteresse, ce qu'il y a à clipper) — utile pour le dialogue Porte 1
- `ARCHIVUM/campaign/reference_skeleton.json` — squelette viral extrait du clip de référence (pré-rempli pour F02)

---

## PATTERN D'EXÉCUTION

F01_SCOUT suit le pattern **3-phases standard** du core YOUTUBE :

```
Phase 1 : prepare
   python scout.py --prepare --directive ../ARCHIVUM/campaign/directive.md
   → génère IN/scout_prompt.json (prompt pour l'IRON)

Phase 2 : IRON (Claude sandbox)
   Le Warsmith copie le prompt dans Claude sandbox.
   L'IRON analyse les assets, extrait métadonnées, calcule l'outlier_score,
   pré-squelette le clip de référence.
   → Écrit OUT/source_specimen.json

Phase 3 : finalize
   python scout.py --finalize
   → Valide cohérence + check-in IW_CUSTOS.py
   → Met à jour liber_clipping.json (statut F01 = done)
```

---

## CONTRATS RÉFÉRENCÉS (ce que F01 doit lire)

- `ARCHIVUM/rules/clipping_rules.md` — règle de strict-source
- `ARCHIVUM/rules/whop_rules.md` — formatted des assets acceptables (vidéos sponsor, etc.)
- `ARCHIVUM/platform_generator/{plateforme}_profile.md` — pour le choix de platform du skeleton
- `CONTRACTS/anti_bullshit.md` (liens core HERESIE/CONTRACTS/) — garde-fous

---

## DÉPENDANCES

- **Amont** : Warsmith (remplit `directive.md` + `reference_clip.json`)
- **Downstream** : F02_TYRANT_CAMP (consomme `source_specimen.json`), F03_SOURCE_HUNTER (consomme `assets[]`)

---

## HÉRÉSIES (ce que F01 ne fait jamais)

- ❌ Chercher des vidéos hors des assets de la campagne
- ❌ Extension du territoire de chasse "en adjacence"
- ❌ Modification/coupe/montage des vidéos sources (cela est boulot d'OMNIS_WATCH)
- ❌ Aucun scrape de concurrents — F00_CAPTEURS s'en charge, pas F01

---

## STATUT

| Phase | État | Notes |
|---|---|---|
| Arborescence créée | ✅ | CODEBASE/libs + IN + OUT + TRACKING |
| TRACKING.md rédigé | ✅ | Ce fichier |
| Code Python implémenté | ✅ | v1 — voir `[DEV-F01]` dans `TRACKING/CLIPPING_LOG.md` |
| `scout.py` | ✅ | Wrapper 3 phases (--prepare / --auto / --finalize) |
| `recon.py` (libs/) | ✅ | Extraction URLs + assets depuis directive.md (section assets, règle C1) |
| `scribe.py` (libs/) | ✅ | Transcription (youtube-transcript-api → yt-dlp subs → dry) |
| `enrich.py` (libs/) | ✅ | Enrichissement yt-dlp --dump-json + outlier_score |
| `requirements_c01.txt` | ✅ | yt-dlp + youtube-transcript-api |

Le futur implémenteur doit s'inspirer de `MONDES_FORGES/YOUTUBE/F01_SENTINEL/CODEBASE/sentinel.py` comme squelette de référence (probablement 80% de réutilisation logique).

*Fer au-dedans, Fer au-dehors.*

## Addendum MEME V2 — intake manuel

F01 accepte une source sociale fournie par le Champion via `--meme-v2-source <json>`. Le JSON d’entrée contient la copie textuelle du tweet ou post Reddit, la capture PNG, l’URL, l’auteur, l’horodatage et les métriques disponibles.

La copie textuelle est archivée dans `OUT/source_post.json` et `OUT/source_specimen.json` pour l’analyse interne. La capture PNG est contrôlée comme fichier existant et devient l’asset visuel destiné au pack final LACRIMAE. Un modèle de vision n’est pas obligatoire si la copie textuelle est fournie ; un contrôle OCR/visuel peut rester optionnel.

F01 ne télécharge pas de clip, ne génère pas de réaction et n’invente aucune métrique. Les valeurs inconnues restent `null`, et une capture absente ou illisible bloque la Gate 1.
