# S01_LOG — Frégate SENTINEL SHORT

> *Étanchéité absolue. Cette frégate ne communique que via liber_perturabo.json.*
> *Le fer qui capture le specimen Short.*

---

## [INIT] S01_SENTINEL SHORT — Structure créée

Frégate de capture de specimen YouTube Short.
Récupère les métadonnées, la transcription et la première frame d'un Short.

### Codebase (à coder)
- `sentinel_short.py` — Capture Short (yt-dlp + youtube-transcript-api + first frame)
- `requirements_s01.txt` — yt-dlp, youtube-transcript-api, requests

### Spécificités Shorts
- Duration ≤ 60s (filtre Short pur)
- First frame extraction (yt-dlp --write-thumbnail)
- Outlier Score SHORTS-specific (views / shorts baseline — pas long baseline)
- View count yt-dlp = ~50% du chiffre page (engaged views vs reely views)

*Fer au-dedans, Fer au-dehors.*
