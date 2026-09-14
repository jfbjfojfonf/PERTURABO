# 12_NOTE_TECHNIQUE — Anti-detection + B-roll Scoring
> Note technique pour OMNIS_WATCH : comment appliquer l'anti-detection et le B-roll scoringué.
---
## 🛡️ Anti-detection
### Pourquoi
Les plateformes comparent les hashes audio/vidéo. Sans traitement, elles détectent la duplication et ban/shadow ban le compte.
### Règle minimale par clip
- **Au moins 1 traitement visuel** (mirror OU zoom OU crop)
- **Au moins 1 traitement audio** (musique OU SFX OU pitch)
- **Zoom invisible** quasi permanent (100% → 108-110%)
- **1-2 SFX** aux moments clés
### Techniques
| Technique | Description | Impact |
|-----------|-------------|--------|
| Mirror flip | Flip horizontal | Élevé |
| Zoom invisible | 100% → 108% lentement | Moyen |
| Speed variation | 1.05x-1.1x | Élevé |
| Crop/reposition | Couper 2-5% des bords | Moyen |
| SFX overlay | Whoosh + boom | Élevé |
### Par style
| Style | Zoom | Mirror | Speed | SFX | Crop |
|-------|------|--------|-------|-----|------|
| Ranking | Punch (110-115%) | Obligatoire | 1.05x | 5-6 | 2-3% |
| Reframing | Slow push (102-108%) | Optionnel | 1.05x | 1-2 | 2-3% |
| Blur | Breathing (105-110%) | Optionnel | 1.05x | 1-2 | Pas nécessaire |
---
## 🎬 B-roll Scoring
### Règle : pas de placement auto après 3s
Chaque segment de 2-3s est scoré. Les meilleurs moments reçoivent le B-roll.
### Facteurs de scoring
| Facteur | Score | Exemple |
|---------|-------|---------|
| visual_trigger | +3 | "she was flirting" |
| context_gap | +3 | "look at what happened" |
| enumeration | +2 | "first, second, third" |
| description_word | +2 | "imagine", "you see" |
| dead_air | +2 | Silence, hésitation |
| emotion_peak | +1 | PAS de B-roll → garder le visage |
### Nombre de B-roll par durée
| Durée | B-roll max |
|-------|-----------|
| 15s | 1 |
| 30s | 3 |
| 45s | 3 |
| 60s | 4 |
### Règles de placement
- **5 secondes minimum** entre chaque B-roll
- **Jamais** sur le hook (0-3s)
- **Jamais** sur l'emotion_peak
- **Toujours** scorer avant de placer
### Sources de B-roll
| Source | Priorité | Action |
|--------|----------|--------|
| Campaign assets | 1 | Cut aux bons timestamps |
| AI generated | 2 | Générer 1-2 si pas assez |
| ARCHIVUM/broll/ | 3 | Chercher des assets stock |
---
## 🎵 SFX Library
| SFX | Usage | Timing | Volume |
|-----|-------|--------|--------|
| whoosh | Transition | Sur chaque cut | -18dB |
| boom | Moment shockant | Sur le punchline | -15dB |
| riser | Montée tension | Avant moment clé | -20dB |
| hit | Accent visuel | Sur zoom/texte | -18dB |
| sub_drop | Grave profond | Moment dramatique | -15dB |
---
## 📐 Format du production_pack_pur.json
```json
{
  "clip_id": "pur_001",
  "style": "ranking",
  "segment": {"start_sec": 45.0, "end_sec": 75.0},
  "text_payload": {
    "title": "TOP 5 MOMENTS",
    "hook_text": "She was flirting with him",
    "captions": [{"text": "...", "start": 0, "end": 2}]
  },
  "broll_schedule": [
    {"id": "broll_1", "source": "campaign/clip.mp4", "cut": {"in": "0:02", "out": "0:05"}, "insert_at_sec": 3.0, "score": 5}
  ],
  "anti_detection": {
    "mirror": true,
    "zoom": {"type": "punch", "start_pct": 100, "end_pct": 115},
    "speed": {"base": 1.0, "variations": [{"at_sec": 15, "speed": 1.05, "duration_sec": 3}]},
    "sfx": [{"type": "whoosh", "at_sec": 3.0, "volume_db": -18}],
    "crop": {"top": 0.02, "bottom": 0.02}
  },
  "montage_instructions": {
    "hook_duration_sec": 3,
    "total_duration_sec": 30,
    "pacing": "fast",
    "energy_curve": ["hook_100", "build_70", "punchline_100", "outro_50"]
  }
}
```
---
## ⚠️ Règles OMNIS_WATCH
1. **Lire le production_pack** — ne rien inventer
2. **Appliquer l'anti-detection** — mirror + zoom + speed + SFX
3. **Insérer les B-roll** — aux timestamps indiqués
4. **Respecter les cuts IN/OUT** — ne pas dépasser
5. **Exporter en 1080p 9:16**
6. **Ne jamais modifier les textes** — ils sont verrouillés
