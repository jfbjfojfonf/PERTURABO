# F03_SOURCE_HUNTER — TRACKING.md

> *"On ne pompe pas le fer au hasard. On choisit la seam, on trace la veinule."*
> *Frégate de sélection des sources. Le Warsmith valide quoi chasser avant la coupe.*

---

## RÔLE

F03_SOURCE_HUNTER est la **frégate de sélection**. À la Porte 3, elle prend les N angles forgés par ANGLESMITH à la Porte 2 et identifie, pour chaque angle, **quelle vidéo longue des assets de la campagne** est la meilleure source à clipper — ainsi que les **segments pertinents** dans cette vidéo.

Elle produit un `source_specimen.json` enrichi (un par angle) qui alimente directement F04_COPYWRITER (qui forge le texte) et F05_PACKAGER (qui emballe le pack).

---

## INPUTS

| Input | Source | Format | Obligatoire |
|---|---|---|---|
| `angles.json` | ANGLESMITH (Porte 2) | JSON | ✅ |
| `source_specimen.json` (assets) | F01_SCOUT | JSON | ✅ |
| `verdict.json` (squelette + blue_ocean) | F02_TYRANT_CAMP | JSON | ✅ |
| `platform_target` | Warsmith | string | ✅ |
| `market_target` | Warsmith | string | ✅ |
| Transcripts des assets | F01_SCOUT (chemin transcript dans ARCHIVUM/campaign/) | JSON | ✅ |

---

## OUTPUTS

### Pour chaque angle, un `OUT/source_specimen_<angle_id>.json`

```json
{
  "campaign_id": "...",
  "angle_id": "...",
  "asset_selected": {
    "asset_id": "...",
    "url": "...",
    "title": "...",
    "duration_sec": N,
    "rationale": "Pourquoi cet asset est le meilleur carrier pour cet angle"
  },
  "suggested_segments": [
    {
      "start_sec": N,
      "end_sec": N,
      "duration_sec": N,
      "rationale": "Ce segment porte l'émotion/engagement que l'angle réclame",
      "extracted_text_snippet": "..."
    }
  ],
  "blue_ocean_reframe_applied": true|false,
  "platform_fit": <0-10>,
  "market_fit": <0-10>,
  "check_in_iw_custos": "<ISO8601>"
}
```

### Autres
- `OUT/source_summary.md` — synthèse lisible Warsmith : "Pour les N angles, voici les sources et segments"

---

## MÉTHODE

### Sélection d'asset par angle
Pour chaque angle, F03 cherche dans `assets[]` (de F01) la vidéo dont le **contenu transcriptuel** match le `reframe_dim` + l'`emotion_mode` de l'angle. L'IRON fait l'analyse qualitative via le transcript, le Warsmith valide le choix.

### Suggested segments
Pour chaque asset sélectionné, F03 propose des **fenêtres temporelles** (start_sec, end_sec) pertinentes pour l'angle. Ces segments sont des **directives** (pas des coupes — la coupe reste à D-F02 d'OMNIS_WATCH). Chaque segment a une `rationale` qualitative.

Règle de durée :
- `clip_max_duration` vient de `platform_generator/{plateforme}_profile.md`
- `clip_min_duration` vient de la même source
- Chaque segment doit être dans la fourchette `[min, max]` de la plateforme cible

### Blue ocean reframe
Si l'angle est en zone océan bleu (cf. `verdict.json`), F03 applique le re-ciblage dans le choix du segment : cherche le segment dont le **sens peut être re-frame** par le texte (cf. `reframe_dim`).

---

## PATTERN D'EXÉCUTION

Pattern **3-phases standard** :

```
Phase 1 : prepare
   python source_hunter.py --prepare --angles ../F02/OUT/angles.json
   → génère IN/source_hunter_prompt.json

Phase 2 : IRON (Claude sandbox)
   Le Warsmith copie-colle le prompt.
   L'IRON lit les transcripts des assets (depuis ARCHIVUM/campaign/),
   les match avec chaque angle, sélectionne asset + segments.
   → Écrit OUT/source_specimen_<angle_id>.json (un par angle)

Phase 3 : finalize
   python source_hunter.py --finalize
   → Valide cohérence + check-in IW_CUSTOS.py
   → Met à jour liber_clipping.json (statut F03 = done, N specimens prêts pour F04)
```

---

## CONTRATS RÉFÉRENCÉS

- `ARCHIVUM/rules/clipping_rules.md` — strict source, jamais sortir des assets
- `ARCHIVUM/platform_generator/{plateforme}_profile.md` — format + durations
- `ARCHIVUM/market_generator/{marché}.md` — contraintes culturelles
- `ARCHIVUM/angles/angle_patterns.json` — patterns d'angles
- `ARCHIVUM/angles/angle_performance.json` — perf passée par angle (poids nul si < 50)
- `CONTRACTS/anti_bullshit.md` (liens core)

---

## DÉPENDANCES

- **Amont** : F01_SCOUT (assets), F02_TYRANT_CAMP (verdict + angles context), ANGLESMITH (angles forgés)
- **Downstream** : F04_COPYWRITER (utilise `suggested_segments` et segments pour forge le texte), F05_PACKAGER (emballe les N specimens + les N text_payloads en N packs)

---

## HÉRÉSIES

- ❌ Sélectionner un asset qui n'est pas dans `source_specimen.assets[]` de F01
- ❌ Couper la vidéo (cela est le boulot de D-F02 dans OMNIS_WATCH — pas F03)
- ❌ Suggérer des segments dont la durée sort de la fourchette plateforme
- ❌ Ignorer `blue_ocean_reframe_applied` quand l'angle est en zone océan bleu

---

## STATUT

| Phase | État | Notes |
|---|---|---|
| Arborescence créée | ✅ | |
| TRACKING.md rédigé | ✅ | Ce fichier |
| Code Python | ✅ | v1 implémentée |
| `source_hunter.py` | ✅ | Wrapper 3 phases (--prepare / --auto / --finalize) |
| `libs/transcript_loader.py` | ✅ | Charge + indexe les transcripts depuis ARCHIVUM/campaign/transcripts/ |
| `libs/segment_matcher.py` | ✅ | Match angle ↔ transcript (banques émotion/reframe), fenêtres clampées, extension au min de durée |
| `libs/duration_guard.py` | ✅ | Fourchette min/max par plateforme (profil ARCHIVUM/platform_generator/, défauts déclarés sinon) |
| `requirements_c03.txt` | ✅ | Stdlib pure (yt-dlp/transcript-api optionnels) |

### Décisions d'implémentation (v1)
- `--prepare` : génère `IN/source_hunter_prompt.json` (mission + angles + assets + fourchette plateforme + hérésies) pour l'IRON.
- `--auto` : analyse locale sans IRON — meilleur asset par angle (score fenêtres transcript), segments dans la fourchette plateforme, `blue_ocean_reframe_applied` calé sur la zone de l'angle.
- `--finalize` : gardes anti-hérésie (asset hors assets F01 = HERESIE, segments hors fourchette, incohérence océan bleu) + `OUT/source_summary.md` + check-in IW_CUSTOS (F03 → `specimens_selected`).
- Le match auto est INDICATIF — chaque score est tracé dans la `rationale`, l'IRON affine en Phase 2.
- La coupe n'est jamais faite par F03 : les segments sont des directives pour D-F02 d'OMNIS_WATCH.

*Fer au-dedans, Fer au-dehors.*
