# Mode MATRICE — Transcription F00B en 15 jobs parallèles

> Ce guide décrit le workflow `perturabo_transcribe_matrix.yml` : la transcription
> d'une VOD en **15 jobs GitHub Actions parallèles** au lieu d'1 job séquentiel.
> Motivation réelle : un run séquentiel de ~3 h d'audio a mis ~1 h au total — et un
> simple push rejeté (`HEAD:main`) a **perdu toutes les sorties**. La matrice divise
> le temps par ~4 ET rend les sorties impérissables (artefacts).

---

## Architecture : 3 jobs au lieu d'1

```
Job 1 "prepare"          Job 2 "transcribe" (matrix ×15)      Job 3 "reassemble"
─────────────            ──────────────────────────────       ──────────────────
· Mesure la VOD          Chaque job :                        · Télécharge les artefacts
  (yt-dlp --dump-json)     · Télécharge SON segment            (download-artifact)
· Découpe en N segments     (~12 min, pas 3 h !)             · Fusionne les transcripts
  (segment_vod.py)        · Transcrit via le service           (merge_transcripts.py :
· Déploie Modal UNE fois    Modal avec OFFSET GLOBAL            déduplication overlap)
· Publie la matrice        (timestamps déjà globaux)         · Scoring GLOBAL
  (outputs GitHub)        · Uploade un ARTEFACT                 (matrix_score.py : chaîne
                            chunk-{id}                          auto_detector inchangée)
                                                            · Commit + push branche live
                                                            · Artefact final (filet)
```

**Temps de run** : ~10-15 min au lieu de ~40-60 min (le facteur limitant devient le
segment le plus lent, pas la somme des segments).

**Coût Modal** : identique — même volume d'audio transcrit, simplement en parallèle.

---

## Le flux de données

1. **`segment_vod.py`** (job prepare) : bornes égales, **overlap 3 s** sur les bornes
   intérieures. Chaque segment porte `offset = download_start` (début RÉEL de la
   tranche téléchargée).
2. Chaque job matriciel télécharge sa tranche avec
   `yt-dlp --download-sections "*start-end"` (+ `--force-keyframes-at-cuts`) :
   **la VOD n'est jamais téléchargée en entier** (règle d'or respectée).
3. Le service Modal (`MODAL/transcribe.py`, champ `offset` du formulaire) ajoute
   l'offset aux timestamps word-level : les mots reviennent **déjà globaux**.
   Rétrocompatible : sans champ `offset`, comportement historique (client relocalise).
4. **`merge_transcripts.py`** (job reassemble) : tri global + déduplication EXACTE
   par `(start, end)` — la zone d'overlap transcrite 2× ne produit aucun doublon.
   Échec volontaire si `< min-words` mots (50) : on ne fabrique pas de candidats
   sur un transcript incomplet.
5. **`matrix_score.py`** : reprend la chaîne d'analyse EXISTANTE
   (`analyze_speech` → `analyze_chat` → `fuse_candidates` → `score_candidates`
   → veto campagne → arbitrage premium). Le chat replay est récupéré globalement
   ici (une seule pagination, zéro douboon). Schéma de sortie IDENTIQUE au run
   séquentiel : `candidats.json` + `auto_detect_report.json` + `transcript.json`
   → même gate opérateur, même chaîne F00D → F04 → F06 → F05 → EXPORT.

---

## Les 3 pièges (et comment ils sont traités)

| # | Piège | Traitement |
|---|---|---|
| 1 | **Deploy Modal dans la matrice** : 15 jobs déploient la même app → collision | Le deploy vit dans `prepare`, l'URL est publiée en output |
| 2 | **Coupures de segments coupent des mots** | Overlap 3 s + déduplication par timestamp global au merge |
| 3 | **Détection par segment** : une fenêtre virale à cheval sur 2 segments est doublée/tronquée | Les jobs matriciels ne font QUE transcrire ; scoring global au reassemble |

Plus le piège historique (l'échec de la session précédente) : **le push final pousse
vers la branche du run** (`HEAD:${BRANCH}`), JAMAIS `HEAD:main`.

---

## Sécurité des sorties (leçon du run perdu)

- Chaque job matriciel **upload un artefact** `chunk-{id}` (7 jours).
- Le job final **upload l'artefact** `final-candidats` (14 jours).
- Même si le commit/push échoue, les sorties restent récupérables dans l'onglet
  Actions du run → Artifacts.

---

## Déclenchement (Oracle uniquement — Porte de déclenchement)

`workflow_dispatch` avec inputs : `vod_url` (requis), `nb_clips` (défaut 5),
`market` (défaut us_young_english), `platform` (défaut youtube_shorts),
`whisper_gpu` (défaut **cpu** — T4 = opt-in, voir guide 15), `nb_segments` (défaut 15).

Secrets requis (identiques au workflow séquentiel) : `MODAL_TOKEN_ID`,
`MODAL_TOKEN_SECRET`, `NVIDIA_NIM_API_KEY`.

Après le run : le gate opérateur valide `v{VODID}_candidats.json` dans
`ARCHIVUM/montage/transcripts/` — c'est LA Porte F00B, rien ne descend la chaîne
sans validation.

---

## Dépannage rapide

| Symptôme | Cause probable | Action |
|---|---|---|
| `Please add a payment method to use T4 GPU functions` | Modal sans carte + `whisper_gpu: T4` | Relancer avec `whisper_gpu: cpu` |
| `CPU is not a valid GPU type` | Ancienne version du service (gpu='cpu') | Version corrigée (paramètre `gpu` omis) — redéployer |
| `updates were rejected (fetch first)` sur le push final | Ancien workflow poussait `HEAD:main` | Corrigé : push sur la branche du run |
| `mots < seuil 50` au merge | Segments échoués en masse | Vérifier les logs des jobs rouges ; relancer (artefacts intacts) |
| Chat vide | GraphQL Twitch raté | Le scoring continue (speech peaks seuls) |
