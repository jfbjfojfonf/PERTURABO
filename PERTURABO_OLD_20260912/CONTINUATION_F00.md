# CONTINUATION — Reprise du siège (F00_CAPTEURS)

> **LIRE CE FICHIER EN PREMIER** si vous arrivez dans ce repo "à froid".
> Il dit EXACTEMENT où le travail s'est arrêté et quoi faire ensuite.

---

## 📅 DERNIÈRE MISE À JOUR

**Date** : 2026-09-05
**Ajout** : F00B_VOX (sous-frégate VOX, l'Oreille Absolue)

---

## 1. État au dernier push

### ✅ Ce qui existe

- **CLIPPING** est opérationnel avec les modes : informatif, humour, meme
- **3 sièges terminés** : NBA_WESTBROOK, STUDENT_DEBT, MARVEL_DOOMSDAY
- **7 frégates actives** : F00A, F00B, F01 → F06
- **ARCHIVUM** enrichi avec channels, campagnes, montage, copywriting, transcripts

### 🆕 Ajouté aujourd'hui

- **F00B_VOX** — L'Oreille Absolue (sous-frégate de F00_CAPTEURS)
  - `F00B_VOX/CODEBASE/f00b_vox.py` — Pipeline complet : ingest → detect → score → gate → trail
  - Ingest VOD partielle (yt-dlp segments HLS, stream copy, jamais de VOD complète)
  - Scoring viral multicritère (6 critères pondérés + bonus/malus)
  - Gate Warsmith (validation manuelle avant trail)
  - Trail prêt pour F03_SOURCE_HUNTER

- **F06_DIRECTOR** — Le Directeur de Montage
  - `F06_DIRECTOR/CODEBASE/director.py` — Génération instructions montage
  - `ARCHIVUM/montage/` — Bibliothèque de montage complète

- **Mode PUR** — Clipping pur (podcast → clip viral)
  - Workflow complet avec F00B_VOX en amont

---

## 2. Les Frégates (mise à jour)

| Code | Nom | Rôle | Statut |
|------|-----|------|--------|
| **F00A** | **CAPTEURS** | **Scan viral YouTube/RSS/Trends** | ✅ Opérationnel |
| **F00B** | **VOX (l'Oreille Absolue)** | **Ingest VOD Twitch partielle + scoring + gate + trail** | 🆕 **Nouveau** |
| F01 | SCOUT | Transcription vidéo | ✅ Opérationnel |
| F02 | TYRANT_CAMP | Verdict GO/NO-GO + océan bleu | ✅ Opérationnel |
| F03 | SOURCE_HUNTER | Sélection segment parfait | ✅ Opérationnel |
| F04 | COPYWRITER | Forger texte viral (frégate lourde) | ✅ Opérationnel |
| F05 | PACKAGER | Emballer production pack | ✅ Opérationnel |
| F06 | DIRECTOR | Instructions de montage | ✅ Opérationnel |

> F00 = F00A (scan viral) + F00B (VOX). La position d'une frégate dépend de SA PLACE dans le workflow, pas d'un numéro figé.

---

## 3. Le Mode PUR — Workflow détaillé

### Inputs du Warsmith
1. URLs VODs Twitch (1 ou plusieurs)
2. Clip viral de référence (optionnel)
3. Plateforme cible (YouTube Shorts / TikTok / Instagram Reels)
4. Marché cible (ex : US / Anglais / Jeune)
5. Nombre de clips demandés

### Workflow
```
F00B_VOX → Ingest VOD partielle + détection candidats + scoring + gate + trail
    ↓ (trail.json)
F01_SCOUT → Transcription complète du segment
    ↓
F02_TYRANT_CAMP → Identifie règles viralité + consulte ARCHIVUM
    ↓
F03_SOURCE_HUNTER → Sélectionne le segment parfait (timestamp précis)
    ↓
F04_COPYWRITER → Forge hook visuel (titres, overlays) + métadonnées
    ↓
F05_PACKAGER → Emballe le production pack (watermark PNG inclus)
    ↓
F06_DIRECTOR → Génère instructions de montage détaillées
    ↓
OMNIS_WATCH → Exécute le montage
    ↓
Opérateur → Poster + soumettre Whop < 1h
```

### Étapes VOX en détail
```
1. IN/vox_input.json → URLs VOD + segments + nb clips demandés
2. python f00b_vox.py ingest → OUT/vox_manifest.json (commandes yt-dlp)
3. IN/signals.json → Signaux (chat spikes, punchlines, trigger words)
4. python f00b_vox.py detect → OUT/candidats.json (fenêtres 20-40s)
5. python f00b_vox.py score → OUT/scoring.json (6 critères pondérés)
6. python f00b_vox.py gate → OUT/gate_verdict.json (skeleton Warsmith)
7. Éditez gate_verdict.json → changez status: pending → approved/rejected
8. python f00b_vox.py gate_apply → Applique les décisions
9. python f00b_vox.py trail → OUT/trail.json (prêt pour F03)
```

### Outputs
- `vox_manifest.json` — Commandes ingest (yt-dlp)
- `candidats.json` — Fenêtres détectées
- `scoring.json` — Scores multicritère
- `gate_verdict.json` — Décisions Warsmith
- `trail.json` — Segments finaux prêts pour F03

---

## 4. F00B_VOX — Détails techniques

### Architecture
```
F00B_VOX/
├── CODEBASE/
│   ├── f00b_vox.py          ← Script principal (CLI)
│   ├── requirements_f00b.txt ← Dépendances (yt-dlp)
│   └── ...
├── IN/                      ← Inputs
│   ├── vox_input.json       ← URLs VOD + segments
│   ├── signals.json         ← Signaux détection
│   └── gate_decisions.json  ← Décisions Warsmith
├── OUT/                     ← Outputs
│   ├── vox_manifest.json
│   ├── candidats.json
│   ├── scoring.json
│   ├── gate_verdict.json
│   └── trail.json
└── TRACKING/
    └── F00B_LOG.md          ← Journal
```

### Scoring Multicritère
```
score = 0.30 × hook_force + 0.25 × emotion + 0.15 × clarity
      + 0.15 × quotability + 0.10 × timing + 0.05 × format_fit
      + bonus - malus
```

### Règles d'or
- ❌ Jamais de VOD complète (segments HLS uniquement)
- ❌ Jamais de recompression (stream copy)
- ❌ Jamais de trail sans verdict gate
- ❌ Budget max 20 min par session

---

## 5. Commandes utiles

```bash
# Pipeline complet (ordre)
python F00B_VOX/CODEBASE/f00b_vox.py ingest        # Génère commandes yt-dlp
python F00B_VOX/CODEBASE/f00b_vox.py ingest --execute  # Exécute les commandes
python F00B_VOX/CODEBASE/f00b_vox.py detect          # Détecte candidats
python F00B_VOX/CODEBASE/f00b_vox.py score           # Score les candidats
python F00B_VOX/CODEBASE/f00b_vox.py gate            # Génère skeleton gate
python F00B_VOX/CODEBASE/f00b_vox.py gate_apply      # Applique décisions
python F00B_VOX/CODEBASE/f00b_vox.py trail           # Génère trails F03
python F00B_VOX/CODEBASE/f00b_vox.py status          # État du pipeline
```

---

## 6. Prochaines étapes

### Court terme
1. ✅ F00B_VOX créé (code + specs + examples)
2. ⏳ Tester avec une vraie VOD Twitch
3. ⏳ Intégrer F00B dans le workflow PUR complet
4. ⏳ Plan 2 : Support campagnes Clipify (watermarks, directives)
5. ⏳ Plan 3 : Mise à jour documentation

### Moyen terme
1. Enrichir ARCHIVUM/montage/ avec plus de patterns
2. Optimiser scoring (IA GPT-4o pour critères subjectifs)
3. Tester le workflow PUR complet de bout en bout

---

*« La VOD est un océan. VOX ne boit que les gouttes d'or. »* 🔩
