# F01_LOG — Frégate SENTINEL

> *Étanchéité absolue. Cette frégate ne communique que via liber_perturabo.json.*
> *Le fer qui voit en premier.*

---

## [INIT] F01_SENTINEL déployée — Codebase complet

Frégate de reconnaissance de la IV Légion. Capture le specimen :
transcription + métadonnées enrichies + outlier score.

### Codebase déployé
- `sentinel.py` — Wrapper orchestrateur (RECON → SCRIBE → enrich → merge → check-in)
- `enrich.py` — Couche d'enrichissement (yt-dlp --dump-json : vues, description, thumbnail, tags, channel, subs)
- `libs/RECON.py` — Copié de youtube-transcriber (listage des vidéos)
- `libs/SCRIBE.py` — Copié de youtube-transcriber (transcription + 2 fallbacks)
- `libs/FORGE.py` — Copié de youtube-transcriber (export JSON)
- `requirements_f01.txt` — yt-dlp, youtube-transcript-api, requests

### Flux interne
1. RECON.run(url) → video_id, title, url, duration
2. SCRIBE.get_transcript() → transcript + timestamps (fallbacks: yt-dlp, timedtext API)
3. enrich.enrich_video() → view_count, description, thumbnail, tags, channel, subscriber_count
4. Calcul Outlier Score = view_count / subscriber_count
5. Merge → specimen.json (OUT)
6. Check-in IW_CUSTOS.py

### Output
`F01_SENTINEL/OUT/specimen.json` — artefact unifié consommé par F02_BREACHER et F05_GRAND_COMPASS.

*Fer au-dedans, Fer au-dehors.*
