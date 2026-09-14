# 11_MODE_PUR — Guide complet
> Le mode **pur** : tu fournis un **podcast/long-form** (transcript + vidéo) + un **style** (ranking/reframing/blur/split_scene) → le forge extrait les moments viraux et produit des clips courts avec hooks, B-roll scoringué, anti-detection et instructions de montage.
---
## 🎯 Le but en 3 lignes
1. Tu donnes un **podcast** (`transcript.json` + vidéo source) → c'est la matière première.
2. Tu choisis un **style** (`ranking`, `reframing`, `blur`, ou `split_scene`) → c'est le traitement visuel.
3. Le forge produit un **production_pack_pur.json** → clip(s) prêt(s) pour OMNIS_WATCH.
---
## 🧾 Les inputs (ce que TU fournis)
### Fichiers à déposer dans `PUR/IN/` AVANT de lancer le siège
| Fichier | Rôle | Exemple |
|---|---|---|
| `transcript.json` | Le transcript du podcast avec timestamps | Transcript YouTube (auto-generated) |
| `directive.md` | Le brief de la campagne | `POST VIRAL CLIPS ... USE STYLE RANKING` |
| `broll_assets.json` | (optionnel) B-roll fournis par la campagne | `{"assets": [{"url": "...", "cut": {"in": "0:02", "out": "0:05"}}]}` |
| `video_source.json` | Métadonnées de la vidéo source | `{"url": "...", "title": "...", "duration_sec": 3600}` |
---
## 🗺️ Le chemin complet — les 4 gates
### Étape 0 — Ouvrir le siège
```bash
cd PUR/CODEBASE
python3 pur.py --start-siege --style ranking
```
→ Crée le `siege_id` (ex : `PUR-SIEGE-20260901T120000`)
→ Vérifie : `python3 pur.py --status`
---
### 🚪 GATE 1 — Le verdict (GO/NO-GO)
**Frégate** : F02 (via import) — vérifie que le podcast est clipable.
```bash
python3 pur.py --verdict
```
**Sortie** : `PUR/OUT/campaign_verdict.json`
| Champ | Signification |
|---|---|
| `verdict` | `GO` ou `NO-GO` |
| `reason` | Pourquoi |
| `clipability_score` | 0-100 (potentiel de clipping) |
**Validation** :
```bash
python3 pur.py --gate 1 --decision valide --notes "podcast clipable"
```
---
### 🚪 GATE 2 — Sélection des moments viraux
**Frégate** : F03 (via import) + `transcript_analyzer.py` — identifie les moments viraux.
```bash
python3 pur.py --select --n-moments 5
```
**Sortie** : `PUR/OUT/viral_moments.json`
| Champ | Signification |
|---|---|
| `moments[]` | Les 5 moments avec `moment_id`, `timestamp`, `hook`, `score` |
| `score` | Score viral (0-10) basé sur les critères ARCHIVUM |
| `emotion_type` | shock / humour / outrage / inspiration |
**Validation** :
```bash
python3 pur.py --gate 2 --decision valide --notes "5 moments scoringués"
```
---
### 🚪 GATE 3 — Copywriting + hooks + B-roll prompts
**Frégate** : F04 (via import) + `broll_scorer.py`
**Oracle** : Génère les titres via clé premium + ARCHIVUM
**Warsmith** : Valide les titres et labels
```bash
python3 pur.py --text --style ranking
```
**Sortie** : `PUR/OUT/text_payload.json`
| Champ | Signification |
|---|---|
| `title` | Titre reframing narratif (≤ 4 mots ranking / ~2 lignes autres) |
| `clip_label` | Label du clip (1 mot, ranking seulement) |
| `hook_text` | Texte du hook (premières secondes) |
| `captions[]` | Transcript du speech (pas de texte écrit) |
| `broll_schedule[]` | B-roll scoringués avec timestamps |
| `metadata` | Titre YouTube, description, tags |
| `copywriting_rules` | Règles de reframing (Oracle → Warsmith) |

#### Le système de titres PUR
| Style | Limite titre principal | Label clip |
|---|---|---|
| **Ranking** | ≤ 4 mots | 1 mot (2 si article) |
| **Blur** | ~2 lignes | Aucun |
| **Split Scene** | ~2 lignes | Aucun |
| **Reframing** | ~2 lignes | Aucun |

#### Le countdown (ranking)
- **#1** = le plus captivant (accroche immédiate)
- **Milieu** = montée en puissance
- **Dernier** = meilleur moment (crescendo)

#### Règles de reframing
- Le titre **TRANSFORME** le sens du contenu (pas une description)
- Le label EST le reframing titre de chaque clip
- Captions = transcript du speech, pas de texte écrit
- Pas de CTA (contenu organique)
- Langue choisie par le Warsmith (FR ou EN)
- ARCHIVUM : `hooks_pur.json` + `copywriting_pur.json`
**Validation** :
```bash
python3 pur.py --gate 3 --decision valide --notes "textes + B-roll validés"
```
---
### 🚪 GATE 4 — Assemblage pack PUR + montage instructions
**Frégate** : F05 (via import) + `montage_builder.py` — assemble le pack final.
```bash
python3 pur.py --assemble --style blur --finalize
```
**Sortie** : `PUR/OUT/production_pack_pur.json`
| Champ | Signification |
|---|---|
| `clip_id` | Identifiant du clip |
| `style` | ranking / reframing / blur |
| `segment` | Timestamp début/fin du moment |
| `text_payload` | Titre, hooks, captions |
| `broll_schedule` | B-roll avec IN/OUT |
| `anti_detection` | Mirror, zoom, speed, SFX, crop |
| `montage_instructions` | Instructions complètes pour OMNIS_WATCH |
**Validation + export** :
```bash
python3 pur.py --gate 4 --decision valide --notes "pack PUR prêt"
python3 pur.py --export
```
---
## 📦 Le livrable final
1. **Copier le pack dans EXPORT/** :
```bash
cp PUR/OUT/production_pack_pur.json EXPORT/production_pack_pur.json
```
2. **Commit + push** :
```bash
git add EXPORT/production_pack_pur.json
git commit -m "CLIPPING: pack PUR exporté"
git push origin main
```
---
## 🎬 Mode Split Scene (4e mode)
Le split_scene est un mode **composable** : clip podcast en haut, titre hook au centre, contenu variable en bas.

### Les 4 sous-layouts
| Sous-layout | Bas = quoi | Quand l'utiliser |
|---|---|---|
| **A_image_ia** | Image IA générée | Pour amplifier l'histoire |
| **B_video_broll** | Clip vidéo / B-roll | Preuve visuelle, autre partie du podcast |
| **C_2_speakers** | Réaction 2e personne | Conversations, interviews |
| **D_preuve** | Tweet, screenshot, stats | Social proof |

### Commandes Split Scene
```bash
# Lancer un siège Split Scene
python3 pur.py --start-siege --style split_scene

# Même pipeline que les autres modes
python3 pur.py --verdict
python3 pur.py --select --n-moments 5
python3 pur.py --text --style split_scene
python3 pur.py --assemble --style split_scene

# Gate 5 : Enrichissement Split Scene (nouveau)
python3 pur.py --direct

# Export
python3 pur.py --export
```

### Règles spécifiques Split Scene
- **Haut** : TOUJOURS le clip podcast (fixe)
- **Centre** : Titre hook (suit `hooks_psychology.json`)
- **Bas** : Variable selon le sous-layout (A/B/C/D)
- **B-roll en split** : couvre TOUT l'écran temporairement
- **GIF** : boucle si un seul, un par numéro en ranking
- **Composabilité** : peut intervenir DANS le ranking
- **Anti-detection** : mêmes règles que les autres modes

---

## ⚙️ Les règles verrouillées
| Règle | Valeur |
|---|---|
| Format | **9:16** (1080×1920) |
| Durée clip | **15-60 secondes** |
| Hook | **0-3 secondes** (visage speaker, pas de B-roll) |
| Anti-detection | **Obligatoire** (1 traitement visuel + 1 audio) |
| B-roll scoring | **Obligatoire** (pas de placement auto) |
| SFX | **1-2 par clip** (whoosh + boom) |
| Zoom invisible | **Quasi permanent** (100% → 108-110%) |
---
## ✅ Checklist rapide
### Avant Gate 1
- [ ] `transcript.json` déposé · [ ] `directive.md` déposé
- [ ] Vérifier que le podcast a du potentiel viral
### Avant Gate 2
- [ ] 5 moments sélectionnés · [ ] Scores différents (pas de doublon)
### Avant Gate 3
- [ ] Titres ≤ 4 mots (ranking) ou ~2 lignes (autres) · [ ] B-roll scoringué
- [ ] Labels clips (1 mot, ranking seulement) · [ ] Oracle a généré · [ ] Warsmith a validé
- [ ] Captions = transcript · [ ] Pas de CTA · [ ] Langue choisie
### Avant Gate 4
- [ ] Anti-detection configurée · [ ] Montage instructions complètes
- [ ] Pack copié dans EXPORT/
---
👉 **Prochaine étape** : `python3 pur.py --direct` → OMNIS_WATCH exécute le montage.
