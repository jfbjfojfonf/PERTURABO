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
