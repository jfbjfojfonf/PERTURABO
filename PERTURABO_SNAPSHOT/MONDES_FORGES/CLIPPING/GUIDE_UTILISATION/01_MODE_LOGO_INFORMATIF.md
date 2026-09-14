# 01_MODE_LOGO_INFORMATIF — Guide complet

> Le mode **logo / informatif** : tu fournis un **article** (le sujet) + une **vidéo background** (illustration, sans lien avec le sujet) → le forge sort N vidéos avec titre viral, paragraphe, metadata, tags, cuts, et le logo de la campagne.
> ✅ Testé en production sur le siège **TS01_SANDOVAL** (Tom Sandoval / TMZ).

---

## 🎯 Le but en 3 lignes

1. Tu donnes un **article** (`article_source.json`) → c'est le VRAI sujet raconté dans les vidéos.
2. Tu donnes une **vidéo background** (`reference_clip.json`) → elle sert d'illustration visuelle uniquement, **aucun lien avec le sujet**.
3. Le forge produit **N vidéos 9:16** (défaut 5) avec texte viral + cuts + **logo de la campagne** → pack expédié à OMNIS_WATCH.

---

## 🧾 Les inputs (ce que TU fournis)

### Fichiers à déposer dans `ARCHIVUM/campaign/` AVANT de lancer le siège

| Fichier | Rôle | Exemple |
|---|---|---|
| `directive.md` | Le brief de la campagne (qui la commande, ce qu'elle demande) | `POST ANY VIRAL CONTENT ... ADD PROVIDED LOGO` |
| `article_source.json` | **LE sujet** : l'article avec `subject`, `key_facts`, `celebrity_or_subject` | Article TMZ Sandoval |
| `reference_clip.json` | La vidéo background : `url`, `title`, `context_article` | Vidéo YouTube E! News (310s) |
| `reference_clip_style.json` | (optionnel) le style viral de référence | squelette viral |

> ⚠️ **Différence clé avec le mode whop** : en mode logo/informatif, il n'y a **pas de F03** (pas de sélection d'asset dans le clip). Le clip background sert juste d'illustration. C'est l'article qui porte le contenu.

---

## 🗺️ Le chemin complet — les 4 gates avec commandes EXACTES

> Toutes les commandes se lancent depuis le `CODEBASE/` de la frégate concernée.
> `python3` = Python 3.10+. Aucune dépendance à installer.

### Étape 0 — Ouvrir le siège

```bash
cd MONDES_FORGES/CLIPPING/ORCHESTRATOR/CODEBASE
python3 orchestrator.py --start-siege
```

→ Crée le `siege_id` (ex : `SIEGE-LOGO-20260804T174153`) et passe `current_porte` à `p1`.
→ Vérifie : `python3 orchestrator.py --status`

---

### 🚪 GATE 1 — Le verdict (GO/NO-GO)

**Frégate** : `F02_TYRANT_CAMP` — vérifie que le clip/la directive est conforme.

```bash
cd ../../F02_TYRANT_CAMP/CODEBASE
python3 tyrant_camp.py --auto --finalize
```

**Sortie** : `F02_TYRANT_CAMP/OUT/campaign_verdict.json` (+ `verdict_report.md`)

| Champ | Signification |
|---|---|
| `verdict` | `GO` (on continue) ou `NO-GO` (on s'arrête) |
| `reason` | Pourquoi |
| `reserve` | Réserve levée / active (ex : mismatch directive vs sujet) |

**Validation** :
```bash
cd ../../ORCHESTRATOR/CODEBASE
python3 orchestrator.py --gate 1 --decision valide --notes "verdict GO conforme directive"
```
*(Si `rejete` → on ne continue pas tant que ce n'est pas corrigé.)*

---

### 🚪 GATE 2 — Les angles (ANGLESMITH)

**Frégate** : `ANGLESMITH` (via F02) — forge N angles viraux, anti-cannibale.

```bash
cd ../../F02_TYRANT_CAMP/CODEBASE
python3 anglesmith.py --auto --n-angles 5 --finalize
```

**Sortie** : `F02_TYRANT_CAMP/OUT/angles.json`

| Champ | Signification |
|---|---|
| `angles[]` | Les 5 angles avec `angle_id` (A01…A05) |
| `angle_family` | reframing / emotion / contrast… |
| `emotion_mode`, `engagement_type` | Pourquoi ça accroche |
| `hook` / `pitch` | L'accroche et le pitch viral |

**Validation** :
```bash
cd ../../ORCHESTRATOR/CODEBASE
python3 orchestrator.py --gate 2 --decision valide --notes "5 angles forgés, anti-cannibale OK"
```

---

### 🚪 GATE 3 — Les textes (F04 COPYWRITER) ⭐ la gate la plus sensible

**Frégate** : `F04_COPYWRITER` — forge les 5 `text_payloads`.

**Étape 3.1 — une seule fois par environnement** : initialiser le system prompt (si jamais fait) :

```bash
cd ../../F04_COPYWRITER/CODEBASE
python3 copywriter.py --init-systemprompt
```

**Étape 3.2 — pour CHAQUE angle (A01 → A05)** :

```bash
python3 copywriter.py --setup-context --angle A01
python3 copywriter.py --generate --angle A01          # AVEC clé premium
python3 copywriter.py --generate --angle A01 --oracle # SANS clé → backup Oracle
python3 copywriter.py --ordonnance --angle A01 --auto-ord   # garde-fou fair use
python3 copywriter.py --finalize --angle A01
```

> 🔑 **La clé premium** : `CLIPPING_PREMIUM_API_KEY` doit être dans API Keys (Freebuff).
> 🧙 **Mode `--oracle`** : si la clé est absente, F04 écrit le prompt dans `F04_COPYWRITER/IN/premium_call_<angle>.json` et **l'Oracle (l'assistant) forge** `F04_COPYWRITER/OUT/text_payload_raw_<angle>.json`. Relance `--generate --oracle` après le forage → ça passe direct.

**Sortie** : `F04_COPYWRITER/OUT/text_payload_A0X.json` (+ `.md` lisible)

| Champ du payload | Règle verrouillée |
|---|---|
| `title` (titre viral) | **≤ 6 mots** |
| `viral_paragraph` | **≤ 4 lignes** |
| `metadata.title` | titre YouTube (peut être plus long) |
| `metadata.description` | **résumé en 2 lignes** + **clause 107 EN** (voir § Règles) |
| `metadata.tags` | **max 12 tags** |
| `on_screen_text` | texte affiché à l'écran (MAJUSCULES, court) |

**Validation** (tu vois les 5 textes COMPLETS dans le chat, pas des résumés) :
```bash
cd ../../ORCHESTRATOR/CODEBASE
python3 orchestrator.py --gate 3 --decision valide --notes "5 text_payloads validés (titre <=6 mots, clause 107 EN, tags)"
```

> ⚠️ **Une fois validée, la gate 3 VERROUILLE les textes.** F04 a fini son travail. La gate 4 ne jugera que les cuts + le pack.

---

### 🚪 GATE 4 — Les cuts + le pack assemblé → EXPÉDITION OMNIS_WATCH

**Frégate** : `F05_PACKAGER` — assemble le pack final.

```bash
cd ../../F05_PACKAGER/CODEBASE
python3 packager.py --assemble --sub-mode informatif --finalize
```

**Sortie** : `F05_PACKAGER/OUT/production_pack_logo.json` (+ `packager_summary.md`, `packs_index.json`)

**Ce que tu valides à la gate 4 :**

| Tu valides | Détail |
|---|---|
| **1. Les cuts** | 5 fenêtres de coupe (ex : A01 `12→47s`) — en mode informatif c'est **PERTURABO qui propose** (`cut_source: perturabo_proposed`) → ta validation les passe en `perturabo_validated` |
| **2. Le pack assemblé** | structure conforme au schéma (0 erreur), 5 vidéos, textes verrouillés + logo |
| **3. L'expédition** | le pack part chez **OMNIS_WATCH** (coupe + rendu 9:16 + logo = leur job) |

**Si tu veux modifier un cut** : édite `ARCHIVUM/campaign/cuts.json` (champ `start_sec`/`end_sec` de l'angle concerné), relance `--assemble`, puis valide.

**Validation + expédition** :
```bash
cd ../../ORCHESTRATOR/CODEBASE
python3 orchestrator.py --gate 4 --decision valide --notes "cuts validés + pack conforme → expédition OMNIS_WATCH"
```

---

## 📦 Le livrable final (après la gate 4)

1. **Copier le pack dans EXPORT/** (le dossier `OUT/` est gitignoré → OMNIS_WATCH ne pourrait pas le récupérer) :

```bash
cd MONDES_FORGES/CLIPPING
cp F05_PACKAGER/OUT/production_pack_logo.json EXPORT/production_pack_logo.json
```

2. **(Optionnel) Créer le ZIP tout-en-un** (pour téléchargement simple) :

```bash
cd EXPORT
python3 -c "
import zipfile, os
z = zipfile.ZipFile('logo_pack_<CAMPAGNE>.zip', 'w', zipfile.ZIP_DEFLATED)
for f in ['production_pack_logo.json', 'packager_summary.md']:
    p = '../F05_PACKAGER/OUT/' + f
    if os.path.exists(p): z.write(p, f)
print('zip créé')"
```

3. **Commit + push GitHub** (tout doit être sur GitHub pour le parachute — si le sandbox meurt, rien n'est perdu) :

```bash
git add MONDES_FORGES/CLIPPING/EXPORT/ MONDES_FORGES/CLIPPING/GUIDE_UTILISATION/
git commit -m "CLIPPING: pack logo <CAMPAGNE> exporté"
git push origin main
```

4. **Les liens raw** (fonctionnent après push) :
- Pack : `raw.githubusercontent.com/<owner>/<repo>/main/MONDES_FORGES/CLIPPING/EXPORT/production_pack_logo.json`
- ZIP : `.../EXPORT/logo_pack_<CAMPAGNE>.zip`

---

## ⚙️ Les règles verrouillées (garde-fous)

| Règle | Valeur |
|---|---|
| Titre viral | **≤ 6 mots** |
| Paragraphe viral | **≤ 4 lignes** |
| Description | **résumé 2 lignes** + **clause 107 EN** |
| Tags | **max 12** |
| Durée minimum du clip | **≥ 7 secondes** |
| Engagement minimum | **≥ 0,8 %** |
| Format | **9:16** (1080×1920) |
| Logo | GIF fourni par la campagne, **position pré-approuvée** (template 1080×1920) — ne pas bouger, redimensionner, recolorer ni couvrir à >50% par des éléments UI |
| Cuts mode informatif | **PERTURABO propose → tu valides** |
| Cuts mode humour | fournis par le Warsmith (`cut_source: operator`) |

**La clause 107 (à garder telle quelle, EN, dans chaque description)** :

> Copyright Disclaimer: Under Section 107 of the Copyright Act of 1976, allowance is made for "fair use" for purposes such as criticism, comment, news reporting, teaching, scholarship, and research. Fair use is a use permitted by copyright statute that might otherwise be infringing. Non-profit, educational or personal use tips the balance in favor of fair use.

---

## ✅ Checklist rapide avant chaque gate

### Avant Gate 1
- [ ] `directive.md` déposé · [ ] `article_source.json` déposé · [ ] `reference_clip.json` déposé
- [ ] Vérifier que le sujet est conforme à la directive (réserve)

### Avant Gate 2
- [ ] Les 5 angles ne se cannibalisent pas (hooks différents)

### Avant Gate 3
- [ ] Titres ≤ 6 mots · [ ] Paragraphes ≤ 4 lignes · [ ] Description = résumé 2 lignes + clause 107 · [ ] Tags ≤ 12
- [ ] TU VOIS LE TEXTE RÉEL COMPLET (pas de raccourci) avant de valider

### Avant Gate 4
- [ ] Cuts dans la durée de la vidéo background · [ ] ≥ 7s par clip · [ ] Pack conforme au schéma (0 erreur)
- [ ] `production_pack_logo.json` copié dans `EXPORT/`

---

👉 **Prochaine étape après le siège** : `F06_TRACKER` — `python3 tracker.py --post` une fois les vidéos publiées (suit vues 1h/24h, payout, learnings).
