# 📋 F06_DIRECTOR — Journal de Déploiement

> *Le directeur de montage veille à ce que chaque seconde compte.*

## État actuel

| Statut | Dernière MAJ |
|--------|--------------|
| **Créé** | 2026-09-01 |
| **Version** | 1.0.0 |
| **Mode** | PUR (clipping pur) |

## Fonctionnalités

### ✅ Implémenté

- [x] `director.py` — Génération des instructions de montage
- [x] `pattern_extractor.py` — Extraction des patterns depuis transcripts
- [x] Règles YouTube Shorts (`ARCHIVUM/montage/rules/youtube_shorts.md`)
- [x] Règles TikTok (`ARCHIVUM/montage/rules/tiktok.md`)
- [x] Règles Instagram Reels (`ARCHIVUM/montage/rules/instagram_reels.md`)
- [x] Patterns par défaut (hooks, zooms, cuts)

### ⏳ En attente

- [ ] Intégration IA (OpenAI/GLM) pour génération avancée
- [ ] Transcripts de tutos montage (à collecter)
- [ ] Tests avec de vrais segments
- [ ] Intégration avec F05_PACKAGER

## Déploiements

### v1.0.0 — 2026-09-01

- Création de la structure F06_DIRECTOR
- Implémentation de `director.py` et `pattern_extractor.py`
- Ajout des règles de montage par plateforme
- Patterns par défaut pour démarrer

## Notes

- F06DIRECTOR est une frégate **passive** — il ne touche jamais à la vidéo
- Il produit des **instructions** que OMNIS_WATCH exécute
- Les patterns s'enrichissent avec chaque campagne (learnings)

---

*"Chaque instruction est un ordre. Chaque seconde est un champ de bataille."*


## v2.0.0-viral — 2026-09-08

- `director.py` RÉÉCRIT : consomme la doctrine réelle d'ARCHIVUM/montage/patterns/ (zoom_patterns, cut_patterns, audio_presets, energy_patterns, anti_detection, text_overlay_patterns, pur_montage_rules, hooks_pur).
- Fini les défauts morts (zoom lent, rouge #FF0000, 'Follow for more'). Désormais : zooms BRUTAUX (brutal_impact + snap_zoom, NO easing), smash/breath/idea cut, SFX sync frame-exacte, courbe d'énergie par émotion, anti-détection obligatoire (mirror + speed + crop + sfx layer + color shift + trim).
- Émotion déduite du signal VOX (punchline -> shock, trigger_word -> outrage, etc.).
- `pur_montage_pipeline.py` : recolle le flux VOX + F04 -> pack COMPLET (source + copywriting + montage_instructions + anti-détection) vers `ARCHIVUM/montage/packs/`. Le pack contient TOUT.
- Nouveau workflow `.github/workflows/perturabo_montage.yml`.

## v2.0.0-viral — frame-près (2026-09-09)

- Calage frame-près : cuts/zooms ancrés sur les vrais timestamps de mots. Plus de grille fixe.
- Chaque événement porte un `word_anchor` exact (ex. A01 snap_zoom@24.43s sur « that? »).
- Doublon `copywriting` retiré des instructions de montage (reste au niveau racine du pack).
- Run vert → packs calibrés A01/A02/A03 + copie EXPORT.
