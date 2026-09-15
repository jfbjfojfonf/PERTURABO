# 14 — Guide Opérateur : Mode PUR

> Ce guide est pour **l'opérateur** (le Warsmith) qui lance un siège PUR.
> Pas besoin de connaître le code. Suivez les étapes.
>
> **2 points d'entrée :** F00B (Twitch) **ou** F00C (YouTube). Ensuite le même tronc.
> Détail technique : guide 20. F00C : guide 19. Vue PUR direct : guide 13.

---

## Checklist rapide

- [ ] Source prête : URL VOD Twitch **ou** URL YouTube
- [ ] Nombre de clips voulu décidé
- [ ] Style choisi : ranking / blur / split / overlay_only (PUR)
- [ ] Directive campagne chargée (ou template rempli)
- [ ] Watermark PNG du créateur dans `watermarks/`
- [ ] yt-dlp + ffmpeg installés (pour ingest réel)

---

## Choisir l'entrée

| Source | Capteur | Commande / Action | Livrable d'entrée du tronc |
|---|---|---|---|
| Twitch (live ou VOD) | **F00B** | Radar live **ou** `f00b_vox.py auto_detect` | `F00B_VOX/OUT/candidats.json` |
| YouTube (live ou vidéo finie) | **F00C** | Actions → « PERTURABO VOX-C ANALYSIS (F00C) » **ou** `f00c_vox.py --to-candidats` | `F00C_VOX/OUT/candidats.json` |

Les deux fichiers ont la **même clé** : `"candidates"`. C'est le schéma canonique.

### Entrée F00C (YouTube) — en 4 clics Actions

1. Capteur : **« PERTURABO VOX-C ANALYSIS (F00C) »** (`to_candidats=true`) → artefact `voxc-candidats-*`
2. Copywriting : **« F04_COPYWRITER PUR (VOX direct) »** (`candidats_path` = artefact, `vod_url` = URL YouTube)
3. Montage : **`perturabo_montage.yml`**
4. ⛔ Gate Warsmith → copie dans `EXPORT/`

Le reste de ce guide détaille le chemin **F00B manuel** (legacy). Le chemin F00B recommandé est `auto_detect` (guide 13).

---

## Étape 1 — Préparer l'input

Créez `IN/vox_input.json` :

```json
{
  "vod_urls": [
    {"url": "https://www.twitch.tv/videos/1234567890", "alias": "stream_01"}
  ],
  "segments": [
    {"alias": "stream_01", "start": "02:14:20", "end": "02:15:00", "id": "seg_01"},
    {"alias": "stream_01", "start": "03:45:10", "end": "03:46:30", "id": "seg_02"}
  ],
  "nb_clips_demandes": 4,
  "budget_max_sec": 1200
}
```

**Règle :** Budget max 20 min par session. Ne téléchargez JAMAIS la VOD complète.

---

## Étape 2 — Ingest

```bash
python F00B_VOX/CODEBASE/f00b_vox.py ingest
```

Ça génère `OUT/vox_manifest.json` avec les commandes yt-dlp.

Pour exécuter (téléchargement réel) :
```bash
python F00B_VOX/CODEBASE/f00b_vox.py ingest --execute
```

---

## Étape 3 — Signaux (optionnel)

Si vous avez des timestamps de moments forts, créez `IN/signals.json` :

```json
{
  "signals": [
    {"start": "02:14:25", "end": "02:14:45", "type": "chat_spike", "intensity": 0.9}
  ]
}
```

Types : `chat_spike`, `energy`, `trigger_word`, `punchline`
Intensité : 0.0 (faible) → 1.0 (très fort)

---

## Étape 4 — Détection + Scoring

```bash
python F00B_VOX/CODEBASE/f00b_vox.py detect
python F00B_VOX/CODEBASE/f00b_vox.py score
```

Ça produit `OUT/candidats.json` et `OUT/scoring.json`.

---

## Étape 5 — Gate (VOTRE VALIDATION)

```bash
python F00B_VOX/CODEBASE/f00b_vox.py gate
```

Ouvrez `OUT/gate_verdict.json`. Pour chaque candidat :
- `pending_warsmith` → Vous devez décider
- Changez en `"approved"` ou `"rejected"`
- Ajoutez un `"motif"` si rejeté

Exemple :
```json
{"candidate_id": "abc123", "status": "approved"}
{"candidate_id": "def456", "status": "rejected", "motif": "pas assez percutant"}
```

Puis :
```bash
python F00B_VOX/CODEBASE/f00b_vox.py gate_apply
```

---

## Étape 6 — Trail final

```bash
python F00B_VOX/CODEBASE/f00b_vox.py trail
```

`OUT/trail.json` contient les segments prêts pour F03_SOURCE_HUNTER.

---

## Étape 7 — Campagne (si applicable)

Si vous avez une directive campagne :

```bash
python ARCHIVUM/campaign/campaign_directive_parser.py \
  ARCHIVUM/campaign/ma_directive.md \
  -o ARCHIVUM/campaign/campaign_directive.json
```

Le JSON produit contient :
- Payouts par plateforme
- Règles caption/tagging
- Règles watermark
- Règles anti-spam

---

## Étape 8 — Poster

1. Lancez F03 → F04 → F05 → F06
2. Récupérez le production pack (clips + watermark + captions)
3. Postez sur les plateformes selon les règles de la campagne
4. Soumettez à Whop dans les délais

---

## Hiérarchie de montage : F00D commande, F06 exécute le reste

Depuis le verrou doctrinal 2026-09-15 (décision opérateur), quand une partition
caviar existe (styles blur/split issus de F00D), **F06 devient consommateur soumis** :

| Possédé par F00D (partition) | Conservé par F06 (soumis) |
|---|---|
| cuts, zooms, punch-ins | text_overlays (overlay F04 validé + captions mot-à-mot) |
| SFX — UNIQUEMENT aux entrées de panneaux (trio broll+flash+SFX) | courbe d'énergie recalée sur le climax caviar |
| miroir, vitesse 1.05×, crop 2.5 % (anti-détection de base) | hiérarchie audio (voix prioritaire) SANS événement SFX |
| rendu des panneaux (crop-zoom, flou, panneau vertical) | anti-détection complémentaire (couche sonore, teinte, trim) |
| duck audio au climax | outro fade/pas de CTA, compliance #ad, règles plateforme |

- Le hook suit **la partition** : panneau posé à ~0 s ⇒ il apparaît à 0 s.
- Chaque output F06 embarque un bloc `caviar_binding` (run_id, checksum) —
  traçabilité de qui a commandé quoi.
- **Style blur sans manifeste caviar ⇒ erreur** (jamais de fallback silencieux).
- Modes sans partition (ranking, overlay_only) : comportement legacy inchangé.

Chaîne complète avec gates (chaque output validé par l'opérateur avant la
frégate suivante) :

```
F00C → 🚧 gate → F00D → 🚧 gate → F04 → 🚧 gate
     → F06 (soumis) → 🚧 gate → F05 (pack final embarquant
     montage_instructions) → 🚧 gate → EXPORT → bras armé
```

---

## Règles d'or

| Règle | Pourquoi |
|-------|----------|
| Jamais de VOD complète | Budget + légal |
| Jamais de recompression | Stream copy uniquement |
| Jamais de trail sans gate | Le Warsmith décide |
| Watermark ≥ 75% | Exigence campagne |
| Pas de CTA | Contenu organique |
| Anti-detection obligatoire | Éviter la suppression |

---

## Commandes rapides

```bash
# Pipeline complet (7 étapes)
python F00B_VOX/CODEBASE/f00b_vox.py ingest
python F00B_VOX/CODEBASE/f00b_vox.py detect
python F00B_VOX/CODEBASE/f00b_vox.py score
python F00B_VOX/CODEBASE/f00b_vox.py gate
# → éditer gate_verdict.json →
python F00B_VOX/CODEBASE/f00b_vox.py gate_apply
python F00B_VOX/CODEBASE/f00b_vox.py trail

# Vérifier l'état
python F00B_VOX/CODEBASE/f00b_vox.py status

# Parser une directive campagne
python ARCHIVUM/campaign/campaign_directive_parser.py directive.md
```

---

## Montage frame-près (F06_DIRECTOR v2)

Le montage est lancé via le workflow `perturabo_montage.yml` (GitHub Actions) : `nb_videos=3, asset_mode=overlay_only`.
Les cuts/zooms sont calés sur les word-timestamps du transcript — plus de grille fixe.
Sorties : `ARCHIVUM/montage/packs/production_pack_Axx.json`. Après gate Warsmith, copie dans `EXPORT/` pour OMNIS_WATCH.

---

## Annexe — Schéma canonique `candidats.json`

Tout capteur (F00B, F00C, futur) DOIT émettre :

```json
{
  "generated_at": "...",
  "source": "...",
  "engine": "...",
  "candidates": [
    {
      "candidate_id": "voxc-1",
      "start_sec": 0.0,
      "end_sec": 0.0,
      "duration_sec": 0.0,
      "signal_type": "platform_heat",
      "signal_intensity": 0.0,
      "signal_start": "...",
      "top_words": ""
    }
  ]
}
```

Le tronc (`pur_adapter_direct`, `pur_montage_pipeline`) accepte aussi l'ancienne clé
`"candidats"` (F00B detect) et un manifeste `perturabo.voxc.v1` — **avec warning**,
jamais en silence. Un fichier vide = erreur, pas 0 pack.

Voir guide 20.

---

*Fer au-dedans, Fer au-dehors. Le siège continue.* 🔩
