# F00B_LOG — Journal de déploiement F00B_VOX

## 2026-09-05 — Auto-Detect v1 (Option A)

**Statut** : ✅ Implémenté, prêt à tester  
**Commit** : feat(F00B): auto_detect v1 — transcription word-level, chat replay, scoring premium

### Fichiers créés/modifiés
- `CODEBASE/libs/__init__.py` → nouveau dossier libs
- `CODEBASE/libs/auto_detector.py` → module auto-detect complet (~470 lignes)
- `CODEBASE/f00b_vox.py` → commande `auto_detect` ajoutée au CLI + flags `--keep-audio`, `--no-chat`, `--market`, `--platform`, `--nb-clips`
- `CODEBASE/requirements_f00b.txt` → documentation des dépendances
- `CONTRACTS/f00b_secrets.example.json` → config clé premium (pattern F04)

### Ce qui a changé
**Avant** : F00B était un constructeur de fenêtres qui exigeait des timestamps humains (signals.json). Le Warsmith devait scrubs la VOD manuellement.

**Après** : F00B détecte automatiquement :
1. **Audio seul** (yt-dlp -f ba, stream copy) → pas de MP4 complet
2. **Transcription word-level** via clé premium (Whisper API OpenAI-compatible, chunks ffmpeg stream copy)
3. **Chat replay Twitch** (API v5 publique, pas d'auth) → pics d'engagement
4. **Speech analysis** (triggers, punchlines, densité)
5. **Fusion + scoring multicritère** → candidats.json
6. **Gate Warsmith** reste obligatoire → le Warsmith valide, il ne détecte plus

### Clé premium
- Config : `CONTRACTS/f00b_secrets.json` (même pattern que F04)
- Env vars : `CLIPPING_F00B_API_KEY` ou fallback `AI_GATEWAY_API_KEY`
- Endpoint : `{base_url}/audio/transcriptions` (OpenAI-compatible)

### Pipeline mis à jour
```
Ancien :  Warsmith fournit timestamps → F00B score → gate
Nouveau : F00B auto_detect → candidats.json → score → gate Warsmith
```

### Commande
```bash
python f00b_vox.py auto_detect --nb-clips 5 --market us_young_english --platform youtube_shorts
```
