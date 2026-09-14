# 20 — NOTE TECHNIQUE : PUR, le pont F00C et l'unité du schéma « candidats »

> *« Une route, deux entrées, un seul tronc. Si l'entrée YouTube ne livre pas le même
> courrier que l'entrée Twitch, le tronc meurt de faim — en silence. »*

---

## 1. Le problème — identifié, avec preuves dans le code

### 1.1 Le tronc commun PUR attend UN schéma d'entrée

Tout l'aval du mode PUR lit les candidats VOX avec la **même clé** :

```python
# pur_adapter_direct.py
candidates = cands.get("candidates", [])

# pur_montage_pipeline.py
candidates = cands.get("candidates", []) if isinstance(cands, dict) else cands
```

Le schéma canonique réel, prouvé par le fichier committé utilisé par les workflows
(`ARCHIVUM/montage/transcripts/v2864600351_candidats.json`) :

```json
{
  "generated_at": "...", "source": "...", "engine": "...",
  "total_words_analyzed": N, "total_candidates_raw": N,
  "total_accepted": N, "total_auto_rejected": N,
  "candidates": [
    { "candidate_id": "...", "start_sec": 0.0, "end_sec": 0.0,
      "duration_sec": 0.0, "signal_type": "...", "signal_intensity": 0.0,
      "signal_start": "...", "top_words": "..." }
  ]
}
```

### 1.2 Les 5 pièges actuels

| # | Piège | Preuve | Effet opérateur |
|---|---|---|---|
| 1 | **F00C s'arrête au manifeste** : `perturabo.voxc.v1` (`viral_segments`) n'est jamais converti en `candidates` | `f00c_vox.py` : aucune commande score/gate/trail, aucun adaptateur | Brancher F00C sur `pur_adapter_direct` → **0 pack, sans aucune erreur** |
| 2 | **Deux clés chez F00B** : `detect` (mode manuel) écrit `"candidats"` ; `auto_detect` écrit `"candidates"` ; les adaptateurs ne lisent QUE `"candidates"` | `f00b_vox.py` L324-337 vs fichier committé v2864600351 | Le chemin « Manuel » du guide 13 donne aussi **0 pack silencieux** |
| 3 | **Aucun workflow YouTube qui commence par F00C** et aboutit au tronc commun | `.github/workflows/perturabo_vox_c_analysis.yml` : artefact = manifeste seul | La chaîne VOX-C → F04 → montage n'existe que dans la tête |
| 4 | **Docs qui ne se renvoient pas la main** : guide 11 (PUR long-form `pur.py`, 4 gates), guide 13 (PUR direct VOX), guide 18 (live Twitch), guide 19 (VOX-C) — le flux PUR direct (F01/F02/F03 SKIPPÉS) n'est explicité nulle part côté F00C | docstring `pur_adapter_direct.py` | L'opérateur suit le mauvais guide et tombe dans les pièges 1-2 |
| 5 | **Deux assembleurs** : guide 11 → GATE 4 via F05_PACKAGER ; PUR direct → `pur_montage_pipeline.py` (F06 inline, F05 absent) | grep vérifié | Confusion sur « qui fait le pack » |

### 1.3 Impact

Toutes ces défaillances sont **muettes** : exit code 0, « 0 candidats », « 0 packs ».
C'est exactement la classe de pièges à éradiquer.

---

## 2. La doctrine cible (une phrase)

**Deux entrées, un tronc, une sortie.** F00B (Twitch) et F00C (YouTube/Twitch/local)
produisent le **même livrable d'entrée** — `candidats.json` au schéma canonique —
puis le tronc commun PUR est inchangé : adaptateur → F04 → F06 → pack → gate
Warsmith → EXPORT → OMNIS_WATCH.

### Carte des parcours (AVANT → APRÈS)

```
AVANT
  Twitch   : F00B (radar live / auto_detect) → candidats → [piège n°2] → tronc (aléatoire)
  YouTube  : F00C → manifeste voxc.v1 → ❌ MUR (aucun pont vers le tronc)

APRÈS
  Twitch   : F00B (radar live ou auto_detect) → OUT/candidats.json (canonique)
             → pur_adapter_direct → F04 → pur_montage_pipeline (F06) → pack → ⛔ gate → EXPORT
  YouTube  : F00C (f00c_vox.py --to-candidats) → OUT/candidats.json (canonique)
             → LE MÊME TRONC, à la lettre
```

---

## 3. Plan de fix — 4 lots

### Lot 1 — Le pont + la tolérance (cœur)

1. **`f00c_vox.py --to-candidats`** : après l'analyse, mappe chaque `viral_segment`
   en candidat canonique :
   - `candidate_id` = `voxc-<rank>` (ou dérivé de la source)
   - `start_sec`/`end_sec`/`duration_sec` = repris du segment
   - `signal_type` = `"platform_heat"` (nouveau type, documenté)
   - `signal_intensity` = `attention_norm`
   - `signal_start` = ISO de l'analyse, `top_words` = `""` (pas de transcript côté F00C)
   - option `--top N` (limiter les N meilleurs segments, défaut : tous)
   Écrit `OUT/candidats.json` (clé `candidates`). Le manifeste reste produit
   inchangé (l'Oracle garde ses données brutes).
2. **Lecteur tolérant dans le tronc** (`pur_adapter_direct.py` + `pur_montage_pipeline.py`) :
   accepte `candidates` **ou** `candidats` **ou** un manifeste `voxc.v1`
   (`viral_segments` → conversion interne), avec **warning explicite** quand la forme
   n'est pas canonique. Élimine les pièges 1 et 2 à la racine.
3. **Tests** : fixtures locales (les 3 formes d'entrée) — pont, lecteur tolérant,
   dégradation propre (manifeste vide → erreur claire, pas de silence).

**Critère de sortie** : pytest vert ; `pur_adapter_direct --candidats <voxc manifest>` produit N angles au lieu de 0.

### Lot 2 — Workflows : les deux entrées officialisées

- **`perturabo_vox_c_analysis.yml`** : nouvel input `to_candidats` (défaut `true`)
  + étape pont + **2e artefact** `voxc-candidats-*` (le `candidats.json`).
- **Chaînage documenté (aucun méga-workflow, on réutilise l'existant)** :

| Étape | Twitch (entrée F00B) | YouTube (entrée F00C) |
|---|---|---|
| 1. Capteur | Radar live / `f00b_vox.py auto_detect` | Actions → **« PERTURABO VOX-C ANALYSIS (F00C) »** (`to_candidats=true`) |
| 2. Copywriting | Actions → **« F04_COPYWRITER PUR (VOX direct) »** avec `candidats_path` + `vod_url` (Twitch) | idem, `candidats_path` = fichier de l'artefact F00C, `vod_url` = URL YouTube |
| 3. Montage | Actions → **« perturabo_montage.yml »** | idem |
| 4. Gate + EXPORT | ⛔ validation Warsmith → copie dans `EXPORT/` | idem |

### Lot 3 — Mise à jour de TOUS les docs (l'utilisateur ne tombe plus dans les pièges)

| Fichier | Modifications |
|---|---|
| `GUIDE_UTILISATION/19_MODE_VOX_C_YOUTUBE.md` | Nouvelle section « Le flow PUR complet depuis F00C » : pont, chaînage des 3 workflows, gate, EXPORT |
| `GUIDE_UTILISATION/13_MODE_PUR_VOX_ET_CAMPAGNES.md` | Tête de guide : « 2 entrées possibles : F00B (Twitch) ou F00C (YouTube) » + pointeur vers guide 20 |
| `GUIDE_UTILISATION/14_GUIDE_OPERATEUR_PUR.md` | Le parcours opérateur branché sur les deux entrées ; le schéma canonique en annexe |
| `GUIDE_UTILISATION/11_MODE_PUR.md` | Encadré de désambiguïsation : PUR long-form (`pur.py`, 4 gates, F05) **vs** PUR direct (VOX → F04, F06 inline) — quand utiliser quoi |
| `README_V2.md` | Carte des deux parcours d'entrée (Twitch / YouTube) + tableau des workflows par étape |
| `CONTINUATION_F00.md` | Session de fix + la règle « tout nouveau capteur émet le schéma canonique » |
| `F00C_VOX/TRACKING/F00C_LOG.md` + `F00C_GATES.md` | Entrées de journal : le pont, les tests, le workflow étendu |
| `GUIDE_UTILISATION/_PIEGES_APPRIS_PUR.md` | Les 5 pièges de cette note, avec le correctif de chacun |

### Lot 4 — Livraison

- Commits sur **`v2-live-vox-c`** (jamais direct sur `v2-live`) au style du repo.
- Push exécuté par **l'agent autorisé sur PERTURABO (kioka)** : kit prêt
  (bundles rafraîchis + arbre STAGING + checklist de réception : pytest 8/8+N,
  workflows visibles, guides à jour).

---

## 4. Règles anti-régression (pour ne plus jamais retomber dedans)

1. **Un seul schéma d'entrée du tronc** (`candidates`, 8 champs) — tout nouveau
   capteur DOIT l'émettre, test à l'appui.
2. **Les lecteurs du tronc sont tolérants mais verbeux** : forme non canonique =
   warning dans les logs, jamais de silence.
3. **Chaque guide commence par son point d'entrée** (F00B ou F00C) et pointe vers
   le guide suivant — chaîne de navigation fermée.
4. **Toute divergence de flux est nommée** avec son cas d'usage (long-form 4 gates
   vs direct) — jamais deux chemins non étiquetés.
5. **`_PIEGES_APPRIS_PUR.md` est le registre vivant** : chaque nouveau piège
   découvert y entre le jour même.

---

*Note 20 — le Fer relie ce qu'il a forgé. Deux entrées, un tronc, une sortie.* 🔩
