# CAPT_LOG — Les Capteurs : Le Fer qui Veille

> *Perturabo ne dormait jamais. Ses Capteurs non plus.*
> *Le fer qui veille ne participe pas au siège — il nourrit l'analyse.*

---

## [INIT] CAPTEURS déployés — Codebase complet

Les Capteurs de la flotte PERTURABO. Surveillance continue des chaînes concurrentes.
Nourrissent l'ARCHIVUM automatiquement et alertent le TYRANT sur les signaux viraux.

### Codebase déployé
- `iron_sentinel.py` — Sweep principal : scanne les chaînes, capture les vidéos, archive les transcripts
- `pattern_capture.py` — Détecte les patterns viraux (Outlier Score > 10 = ROUGE, > 3 = JAUNE)
- `alert_system.py` — Génère les alertes pour le TYRANT (latest_alert.json)
- `requirements_capt.txt` — yt-dlp, youtube-transcript-api, requests

### Flux
1. GitHub Actions (iron_sentinel.yml) lance iron_sentinel.py tous les jours à 2h
2. iron_sentinel.py lit monitored_channels.json (CAPTEURS/IN/)
3. Pour chaque chaîne : yt-dlp --flat-playlist → liste les vidéos récentes
4. Pour chaque nouvelle vidéo : youtube-transcript-api → transcription
5. yt-dlp --dump-json → view_count, subscriber_count
6. Calcule l'Outlier Score = view_count / subscriber_count
7. Archive la transcription dans ARCHIVUM/transcripts/
8. pattern_capture.py classifie les signaux (ROUGE / JAUNE)
9. alert_system.py génère latest_alert.json pour le TYRANT
10. Le TYRANT lit latest_alert.json à la prochaine Porte 1

### Seuils de signaux
- Outlier Score > 10.0 → SIGNAL ROUGE (vidéo virale massive)
- Outlier Score > 3.0 → SIGNAL JAUNE (vidéo qui performe bien)
- Outlier Score < 3.0 → Pas de signal

### Input
`CAPTEURS/IN/monitored_channels.json` — liste des chaînes à surveiller

### Output
- `CAPTEURS/OUT/signals/` — rapports de sweep (JSON par sweep)
- `CAPTEURS/OUT/latest_alert.json` — alerte synthétisée pour le TYRANT
- `ARCHIVUM/transcripts/` — transcriptions archivées (nourrit la Mémoire Impériale)

### Coût : 0.00 EUR (Axiome I respecté — yt-dlp + youtube-transcript-api gratuits)

*Fer au-dedans, Fer au-dehors.*
