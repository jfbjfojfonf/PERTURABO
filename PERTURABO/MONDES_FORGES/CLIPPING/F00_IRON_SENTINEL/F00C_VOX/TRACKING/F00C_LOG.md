# PERTURABO v2-live — F00C_VOX JOURNAL DE CAMPAGNE

> *Chaque entrée est immuable. Une fois écrite, elle ne s'efface pas.*

| Date | Source analysée | Statut | Segments | Run CI | Décision Warsmith |
|---|---|---|---|---|---|
| 2026-09-14 | Transcripts : source opérateur `transcripts_in/` + filet Whisper local ajoutés (priorité opérateur > cache > YouTube > Whisper) | LIVRÉ (29 tests verts) | — | — | Déposer `cP8vli4kfhs.fr.srt` + `.en.srt` dans `war_room/transcripts_in/` |
| — | — | — | — | — | — |

### 2026-09-13 — WAR ROOM v3 : contrôle opérateur + transcripts bilingues

- **RESET global** : bouton rouge dans le header (confirmation obligatoire) →
  `POST /api/reset` purge tous les verdicts + compteurs (`{"full":true}` vide
  aussi les runs). Les manifestes caviar restent traçables côté F00D.
- **Révocation individuelle** : tag « ✔ GO » / « ✘ NO-GO » cliquable + bouton
  « ✕ retirer » sur chaque carte votée → `verdict: "clear"` → la carte redevient
  en attente, compteurs décrémentés proprement.
- **Transcripts FR | EN** : clic sur une carte → panneau bilingue horodaté
  (plage du clip surlignée). Source : sous-titres YouTube (manuels puis auto)
  via **yt-dlp vendored** (`war_room/_vendor/`, aucune installation requise).
  Cache : `docs/data/transcripts/{run_id}/{candidate}.{fr|en}.json`.
- **Préchauffage** : à l'arrivée d'un run, tous les transcripts se téléchargent
  en tâche de fond (thread daemon) — le clic opérateur reste instantané.
- **Rate-limit 429** (survenu en réel pendant l'implémentation) : message
  lisible « YouTube limite le débit de cette IP — nouvel essai dans ~10 min »
  + cooldown par vidéo ; le préchauffage retente après expiration. Zéro crash.
- **Garde-fou anti-mélange de runs** : `_load_caviar_index(run_id)` refuse les
  manifestes caviar émis pour un autre run (les ids voxc-N se répètent d'un
  run à l'autre — ne jamais servir l'ancien au cockpit).
- **Tests** : 21/21 verts (récepteur + gate/reset + transcripts). Self-tests
  `receiver.py` et `transcripts.py` OK.
- **Leçon → Archivum F00D** : YouTube rate-limite les IPs datacenter sur les
  sous-titres → toujours prévoir cache + cooldown + retry asynchrone, jamais
  de téléchargement bloquant au clic.
## Entrées de mise en service

### 2026-09-13 (ter) — NAISSANCE F00D_NARRATIVUM (sous-frégate compositeur)

- **Décision Warsmith** : nouvelle sous-frégate sœur (F00D), mission unique :
  candidat validé → `caviar_manifest.json` (caviar.v1) pour le bras armé.
- **Placement** : `F00_IRON_SENTINEL/F00D_NARRATIVUM/` (sœur de F00B/F00C —
  appelée par les deux ; jamais de copie divergente).
- **Archivum** : mémoire dans `ARCHIVUM/montage/narrativum/` (règle flotte :
  pas d'Archivum dans l'Archivum) — ledger, gate_history, retention_log, lessons.
- **Budget d'Attention** : `caviar_budget.json` (100u/clip, plafond 55u,
  trio B-roll+flash+SFX = 12u, smash 8u, punch-in 6u, jump-cut 1u + caps).
  Transmis au bras armé pour ses gates P-CAV (double barrage).
- **3 styles** : split (b-roll sur la moitié jeu, punch-in webcam), reframing
  (overlay frame 0 jusqu'au climax), ranking (trio à l'entrée d'item, smash
  bonus sur l'item #1). Constante : le trio RACCOURCIT le pacing local et
  l'audio du streamer est MAINTENU.
- **Règles d'or** : SFX uniquement à l'entrée B-roll ; flash entrée uniquement ;
  référentiel = secondes relatives au segment ; la frégate refuse d'émettre
  un manifeste saturé (pas de toxique — diagnostic à la place).
- **Code** : `caviar_director.py` (silencedetect, numpy amplitudes, composition
  par style, budget, émission + ledger). Tests : 8/8 verts + self-test OK.
- **Prochain** : premier manifeste réel sur un candidat Sophie Rain gate GO.

### 2026-09-13 (bis) — RUN RÉEL 1 h 42 + RÉCEPTEUR DURCI (fin du HTTP 400)

- **Run réel complet** : `cP8vli4kfhs` (« How Sophie Rain Makes And Spends
  $100,000,000 Per Year », 6156 s) — téléchargement 144p ~45 Mo, heatmap
  120 buckets, **barre rouge Most Replayed récupérée** (100 points — YouTube
  l'expose pour cette vidéo, contrairement à l'extrait de 8 min), fusion
  active, 5 candidats, couverture **100 %**. Webhook poussé automatiquement
  en fin de run — le dashboard s'est rempli sans intervention.
- **Incident corrigé** : le récepteur est tombé après la poussée (proxy →
  HTTP 400 côté navigateur). Durcissement `receiver.py` : try/except global
  sur do_POST/do_GET — une erreur interne répond **JSON 500** au lieu de tuer
  le serveur ; BrokenPipe ignoré (client parti avant réponse).
- **Hygiène de l'état** : les tests pytest écrivent désormais dans un fichier
  temporaire (le vrai `war_room.json` n'est plus jamais touché) ; le
  self-test **sauvegarde et restaure** l'état réel ; pollution démo purgée
  de l'historique (runs/gates/verdicts réels uniquement).
- **Miroir** : récepteur + dashboard + état d'exemple archivés dans
  `F00C_VOX/WAR_ROOM/` (PERTURABO garde une copie de son siège).
- **Tests** : F00C 25/25 · récepteur 11/11 (isolés) · self-test non destructif.

### 2026-09-13 — AUDIT WARSMITH + CONTRAT V2 (le dashboard ne devine plus)

- **Audit du Warsmith sur la preview** : file des candidats vide, pas d'axes,
  rien de cliquable, légende mensongère, doute « 8 min sur une vidéo plus longue ».
- **Cause racine (bug bloquant)** : le dashboard lisait `c.id`/`c.score`/`c.rank`
  tandis que F00C pousse `candidate_id`/`signal_intensity` — TypeError JS avalé
  en silence par `catch(_)` → liste vide, gate envoyant `undefined`.
- **Fait établi** : la 1re URL (`qm3E3cchBmQ`) = 514 s réels (`not_live`, confirmé
  yt-dlp) — F00C a analysé 100 % de cette vidéo. Le doute venait de l'absence de
  durée affichée. Nouvelle URL du Warsmith (`cP8vli4kfhs`) = 6156 s (1 h 42).
- **Contrat V2 (`build_webhook_payload`)** : chaque candidat part avec `id`,
  `rank`, `score /100`, `start_label`/`end_label` (m:ss), `vs_mean_pct`,
  `platforms` ; le run porte `title`, `channel`, `duration_total_sec`,
  `analyzed_duration_sec`, `coverage_pct`, `mean_attention`, `replayed_note`.
- **Dashboard v2 (docs/war_room.html)** : axe X gradué (m:ss), axe Y 0→1,
  tooltips exacts au survol, candidats cliquables ↔ timeline, cartes complètes
  (durée, position %, intensité vs moyenne, barre métrique), légende truthful
  (présente/absente), histogramme de distribution, bandeau couverture
  (« analysé X / Y — ✔ complet »), bandeau d'erreur (fini le silence).
- **Workflow runner** : installation de deno ajoutée (runtime JS exigé par
  yt-dlp pour les challenges n/sig — warning observé au test local).
- **Tests** : 25/25 verts (2 nouveaux : enrichissement V2 + labels m:ss).
- **Territoire intact** : F00B (docs/index.html + radar) NON touché.

### 2026-09-12 — LIVRAISONS C+D : Salle de Guerre complète (dashboard + mode LIVE + gate cockpit)

- **Récepteur v2** (`WAR_ROOM/receiver.py`, miroir dans ce repo) : sert le
  dashboard (`GET /` → `docs/war_room.html`), `GET /api/war-room` (polling),
  `POST /api/gate` (verdicts Warsmith, sans token — cockpit navigateur),
  `POST /` webhook F00C (X-Siege-Token). Port : `--port` > env `PORT` > 8787.
- **Boucle de retour Livraison D fermée** : le dashboard poste GO/NO-GO sur
  `/api/gate` → stocké dans `war_room.json` (`gates`, idempotent : re-voter
  identique ne gonfle pas les compteurs, une inversion remplace le compteur
  précédent) → le pipeline PERTURABO relit `GET /api/war-room` pour connaître
  les clips GO.
- **Dashboard** (`docs/war_room.html`, thème Iron Warriors) : timeline SVG
  (heatmap capteur or + barre rouge most-replayed pointillée + fusion or vif +
  blocs candidats), cartes triées par score avec boutons **GO / NO-GO**,
  badge mode VOD/LIVE pulsé (poll 2 s), nouveaux candidats marqués `NEW` en
  LIVE, **toggle DONNÉES BRUTES** (le JSON réel affiché tel quel).
- **Seed démo** (`WAR_ROOM/seed_demo.py`) : payload Sophie Rain synthétique
  conforme au contrat (100 buckets, barre rouge 25 pas, fusion 0.6/0.4,
  3 candidats) — l'état affiché tant que le run réel n'a pas poussé.
- **Tests** : 11/11 verts côté récepteur (gate inconnue, candidate fantôme,
  idempotence des compteurs) + self-test round-trip.

### 2026-09-12 — LIVRAISON B : barre rouge Most Replayed + webhook Salle de Guerre

- **Barre rouge** : `--fetch-replayed` → `yt-dlp --dump-json` (zéro média
  téléchargé, escalier habituel) → `replayed_curve` [{start, end, value}] dans
  le manifeste. Indisponible ⇒ `replayed_note` explicite (jamais de silence).
- **Fusion** : `fused_heatmap = 0.6 × attention_norm (capteur) + 0.4 ×
  replayed_norm (humains réels)` — le croisement capteur × comportement.
  Sans barre rouge : `fused = attention_norm`, `replayed_applied: false`.
- **Webhook** : `--webhook-url` (+ `X-Siege-Token`, défaut env
  `SIEGE_WEBHOOK_TOKEN`) → payload contrat §4 (run_id, siege_id, mode
  vod|live, status, heatmap, replayed_curve, fused_heatmap, candidates,
  pushed_at). Échec réseau = warning, le manifeste local reste le livrable.
- **Workflow** : `--fetch-replayed` toujours actif, input `webhook_url` +
  secret `SIEGE_WEBHOOK_TOKEN`.
- **Récepteur de référence** (repo kbkjhjhl) : `war_room/receiver.py` —
  validation stricte (422 si payload invalide, 401 si token), stockage
  `docs/data/war_room.json` (last_run + historique), `GET /api/war-room`
  pour le dashboard. 8/8 tests + self-test round-trip verts.
- **Tests** : 23/23 verts côté F00C (6 nouveaux : parsing dump-json,
  note non silencieuse, fusion avec/sans barre rouge, payload canonique,
  envoi token+payload).
- **Docs** : guide 19 (section « barre rouge et webhook »).

### 2026-09-12 — LIVRAISON A : escalier anti-anti-bot + garde-fou + contrat découplé

- **Code (`f00c_vox.py`)** :
  - `download_media()` réécrite — escalier 3 marches : `player_client=ios,mweb`
    (gratuit) → yt-dlp nu → `--cookies` (session burner). Formats video-only
    `height<=144` (défaut) : la heatmap réduit à 64×36, ~30-60 Mo/h au lieu de Go.
  - **Contrat découplé** `--media-source` : métadonnées = URL source, média =
    fichier local séparé (piste fichier disponible sans dépendre de YouTube).
  - **CLI `--cookies-file`** pour la session burner.
- **Garde-fou anti-faux-vert** : CLI exit 2 si `download_budget_seconds > 0` et
  (`status != "full"` sans `--media-source`, ou 0 candidat avec `--to-candidats`).
  Workflow : étape GUARD dédiée (exit 1, message « Analyse fonctionnelle échouée… »)
  + `if: always()` pour couvrir les échecs d'étapes amont.
- **Workflow** : secret `YT_COOKIES_BASE64` → `/tmp/yt_cookies.txt` (`umask 077`,
  jamais loggé) → `--cookies-file` → **détruit en fin de job** (`if: always()`).
  Input `media_source` ajouté. `pip install --upgrade yt-dlp` (course anti-bot).
- **Tests** : 17/17 verts (9 bridge + 8 voxc) — régression zéro.
- **Docs** : guide 19 (section « Le mur anti-bot et l'escalier » + protocole cookies
  burner + 2 hérésies), `requirements_f00c.txt` (escalier documenté), CONTINUATION.
- **Reste côté Warsmith** : créer le burner, coller `YT_COOKIES_BASE64` dans les
  secrets GH, rotation hebdo. Ensuite : relancer le run Sophie Rain (86400 s) —
  attendu `status: full` sinon échec explicite.

### 2026-09-11 — PORTAGE INITIAL (lot 1+2)

- **Origine** : `f00_live.py` porté depuis LACRIMAE `dev10-v3-live`
  (commit `d1b182c`, tests 8/8 verts) et adapté aux conventions F00B.
- **Créé** :
  - `CODEBASE/f00c_vox.py` — resolve → metadata (YouTube public / Twitch GQL) →
    heatmap d'attention (numpy + ffmpeg, média local) → manifeste
    `perturabo.voxc.v1` (metadata, attention_heatmap, viral_segments pics ≥ 5 s,
    raw_data Oracle). Live EN COURS et vidéo FINIE : même pipeline.
  - `CODEBASE/tests/test_f00c_vox.py` — 8 tests hors-ligne, **8/8 verts**.
  - `CODEBASE/requirements_f00c.txt` — stdlib pour l'analyse ; yt-dlp + ffmpeg
    système pour l'ingest (doctrine F00B respectée) ; numpy pour la heatmap.
  - `IN/vox_c_input.example.json`, workflow `.github/workflows/perturabo_vox_c_analysis.yml`
    (dispatch manuel, gate L0, artefact `voxc-analysis-*`).
- **Note de nommage** : dans LACRIMAE, `F00C` désigne déjà « Motion Slow »
  (interpolation). Dans PERTURABO, F00C était libre — F00C_VOX vit ici, pas
  de collision au sein du repo. À ne pas confondre entre repos.
- **Doctrine** : jamais de VOD complète (`--download-sections` uniquement),
  jamais de recompression, jamais de manifeste vide (metadata_only reste
  un livrable pour l'Oracle).

### 2026-09-12 — PLAN_SALLE_DE_GUERRE (diagnostic + plan, aucun code)

- **Run réel raté (Sophie Rain)** : workflow lancé avec `download_budget_seconds=86400`
  → yt-dlp bloqué « Sign in to confirm you're not a bot » (IP datacenter du runner)
  → `status: metadata_only`, 0 segment, 0 candidat — **mais workflow VERT** (faux succès).
- **Diagnostic acté** : le blocage est identitaire (IP datacenter), pas de configuration.
  L'API YouTube ne donne que les métadonnées ; la heatmap vidéo exige le média.
- **Plan validé par le Warsmith** : `PLAN_SALLE_DE_GUERRE.md` (à la racine F00C_VOX).
  Combinaison retenue : **contrat découplé** (`--media-source`, metadata ≠ média)
  + **cookies burner** (secret `YT_COOKIES_BASE64`, fichier temporaire détruit en fin
  de job, rotation hebdo) + **garde-fou anti-faux-vert** (exit 1 si budget > 0 et
  `status != "full"` ou si `to_candidats` avec 0 candidat) + téléchargement 144p
  video-only + **Most Replayed** (barre rouge YouTube fusionnée à la heatmap vidéo).
- **Ajouts issus du brainstorm externe** : test gratuit `player_client=ios,mweb` en
  Étape 0 ; hook words / seamless loop en backlog. **Refusés** : Ragebait (viole la
  directive : pas de bait/misinfo/PR négative), scramble d'empreinte audio.
- **Salle de Guerre** (workspace Freebuff, Vite+Convex, repo `kbkjhjhl`) : webhook
  `X-Siege-Token` ← PERTURABO ; dashboard `/war-room` avec timeline heatmap + barre
  rouge + candidats, toggle DONNÉES BRUTES, mode VOD (tout d'un coup) et mode LIVE
  (temps réel), gate Warsmith inline (GO/NO-GO par carte).
- **Règle de territoire rappelée** : F00B = Twitch uniquement. La campagne Sophie Rain
  (YouTube) ne touche que F00C.
- **Prochaine étape** : Livraison A (Phases 0-4 du plan) dès le GO du Warsmith.

### 2026-09-11 — PONT F00C → TRONC PUR (Note 20)

- **`--to-candidats`** + `--top N` : `viral_segments` → `OUT/candidats.json`
  (clé `candidates`, `signal_type: platform_heat`, intensité = `attention_norm`).
- **Lecteur tolérant** `SHARED/candidates_reader.py` branché dans
  `pur_adapter.py`, `pur_adapter_direct.py`, `pur_montage_pipeline.py`.
- **Workflow** : input `to_candidats` (défaut true) + artefact `voxc-candidats-*`.
- **Tests** : `test_candidates_bridge.py` (3 formes + vide = erreur, pas de silence).
- **Docs** : guides 11/13/14/19/20, README_V2, CONTINUATION_F00, `_PIEGES_APPRIS_PUR.md`.
