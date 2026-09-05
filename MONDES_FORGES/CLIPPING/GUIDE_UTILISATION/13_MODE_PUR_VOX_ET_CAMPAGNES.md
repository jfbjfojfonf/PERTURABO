# 13 — Mode PUR : VOX + Campagnes Clipify

> Le mode PUR extrait des clips viraux depuis des VODs Twitch.
> VOX est la sous-frégate qui ingère, détecte, score et trail les candidats.
> Les campagnes Clipify/Whop définissent les règles de publication et de payout.

---

## 1. Vue d'ensemble

```
Warsmith → URLs VODs + nb clips + directive campagne
    ↓
F00B_VOX → ingest → detect → score → gate → trail
    ↓ (trail.json)
F01_SCOUT → F02_TYRANT_CAMP → F03 → F04 → F05 → F06
    ↓
Opérateur → poster + soumettre Whop
```

**Ordre PUR mis à jour :**
F00B_VOX → F01 → F02 → F03 → F04 → F05 → F06

---

## 2. Inputs du Warsmith

### IN/vox_input.json (obligatoire)
```json
{
  "vod_urls": [
    {"url": "https://www.twitch.tv/videos/1234567890", "alias": "stream_main"}
  ],
  "segments": [
    {"alias": "stream_main", "start": "02:14:20", "end": "02:15:00", "id": "seg_01"},
    {"alias": "stream_main", "start": "03:45:10", "end": "03:46:30", "id": "seg_02"}
  ],
  "nb_clips_demandes": 4,
  "budget_max_sec": 1200,
  "plateforme": "tiktok",
  "directive_ref": "ARCHIVUM/campaign/whop_directive.md",
  "clip_ref_url": null
}
```

### IN/signals.json (optionnel — améliore la détection)
```json
{
  "signals": [
    {"start": "02:14:25", "end": "02:14:45", "type": "chat_spike", "intensity": 0.9},
    {"start": "03:45:30", "end": "03:45:50", "type": "punchline", "intensity": 1.0}
  ],
  "pre_roll_sec": 2.0,
  "post_roll_sec": 2.0
}
```

---

## 3. Pipeline VOX (commandes)

### Mode Auto-Detect (recommandé)
F00B détecte automatiquement les moments viraux sans input humain :

```bash
# Étape 0 — Auto-detect (audio + transcription word-level + chat replay + scoring)
python F00B_VOX/CODEBASE/f00b_vox.py auto_detect --nb-clips 5
python F00B_VOX/CODEBASE/f00b_vox.py auto_detect --keep-audio --no-chat
python F00B_VOX/CODEBASE/f00b_vox.py auto_detect --market us_young_english --platform youtube_shorts
```

**Prérequis :** yt-dlp + ffmpeg installés, clé premium configurée.
**Clé premium :** `CONTRACTS/f00b_secrets.json` ou env `CLIPPING_F00B_API_KEY` / `AI_GATEWAY_API_KEY`.
**Sortie :** `OUT/candidats.json` (même schéma que detect → score/gate/trail inchangés).

### Mode Manuel (legacy)
```bash
# Étape 1 — Ingest (génère commandes yt-dlp)
python F00B_VOX/CODEBASE/f00b_vox.py ingest

# Étape 1b — Exécuter les commandes (si yt-dlp installé)
python F00B_VOX/CODEBASE/f00b_vox.py ingest --execute

# Étape 2 — Détection candidats
python F00B_VOX/CODEBASE/f00b_vox.py detect

# Étape 3 — Scoring
python F00B_VOX/CODEBASE/f00b_vox.py score

# Étape 4 — Gate (skeleton pour Warsmith)
python F00B_VOX/CODEBASE/f00b_vox.py gate

# Étape 5 — Éditer OUT/gate_verdict.json
# Changez "pending_warsmith" → "approved" ou "rejected"

# Étape 6 — Appliquer décisions
python F00B_VOX/CODEBASE/f00b_vox.py gate_apply

# Étape 7 — Trail final
python F00B_VOX/CODEBASE/f00b_vox.py trail

# État du pipeline
python F00B_VOX/CODEBASE/f00b_vox.py status
```

---

## 4. Scoring Multicritère

| Critère | Poids | Description |
|---------|-------|-------------|
| hook_force | 0.30 | La première phrase arrête-t-elle le scroll ? |
| emotion | 0.25 | Intensité émotionnelle (rire, indignation, surprise) |
| clarity | 0.15 | Compréhensible sans contexte ? |
| quotability | 0.15 | Phrase mémorable, citable ? |
| timing | 0.10 | Rythme interne (peu de temps mort) |
| format_fit | 0.05 | Convient au format vertical 9:16 ? |

**Bonus :** +2 clip ref, +1.5 moment unique, +1 série
**Malus :** -3 durée >60s, -2 contexte requis, -2 TOS risk, -1 caméra

---

## 5. Gate Warsmith

Le gate est une étape **obligatoire**. Aucun clip ne passe au trail sans verdict.

**Protocole :**
1. VOX propose N candidats (N = nb demandé × 2 min)
2. Chaque candidat a : score, top 2 hooks, durée proposée
3. Warsmith VALIDE, MODIFIE ou REJETTE chaque candidat
4. Seuls les `approved` partent au trail

**Règle d'or :** Le Warsmith décide du nombre final. Pas de clip sans verdict.

---

## 6. Campagnes Clipify/Whop

### Template
`ARCHIVUM/campaign/whop_directive_template.md`

### Parser
```bash
python ARCHIVUM/campaign/campaign_directive_parser.py \
  ARCHIVUM/campaign/ma_directive.md \
  -o ARCHIVUM/campaign/campaign_directive.json
```

### Champs extraits
- `campaign_id`, `creator_name`
- `platforms` (TikTok, X, IG Reels, YT Shorts)
- `payout.per_platform` ($X per YK views)
- `caption_rules` (handle, hashtags, caption par plateforme)
- `watermark` (opacity, position, platforms obligées)
- `anti_spam` (règles)
- `content_source` (source approuvée, restrictions)
- `cycle` (start, end)

### Exemple réel
`ARCHIVUM/campaign/clipify_aishahsofey_directive.md`

---

## 7. Watermarks

**Règles :**
- Format PNG (transparence)
- Opacité ≥ 75%
- Position centrée
- Taille ≥ 15% de la largeur vidéo
- Obligatoire : TikTok, IG Reels, YT Shorts
- Optionnel : X (Twitter)

**Fichiers :**
- `watermarks/[creator]_watermark.png`
- `watermarks/watermark_rules.json`

**Intégration :** F05_PACKAGER inclut le watermark dans le production_pack.json

---

## 8. Outputs

| Fichier | Généré par | Contenu |
|---------|-----------|---------|
| vox_manifest.json | F00B (ingest) | Commandes yt-dlp |
| candidats.json | F00B (detect) | Fenêtres 20-40s |
| scoring.json | F00B (score) | Scores multicritère |
| gate_verdict.json | F00B (gate) | Décisions Warsmith |
| trail.json | F00B (trail) | Segments prêts F03 |
| campaign_directive.json | Parser | Règles campagne structurées |

---

*Fer au-dedans, Fer au-dehors. Le siège continue.* 🔩
