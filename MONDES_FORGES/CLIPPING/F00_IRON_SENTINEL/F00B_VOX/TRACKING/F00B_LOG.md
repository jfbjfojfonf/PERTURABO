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
2. **Transcription** via clé premium (Whisper API OpenAI-compatible, chunks ffmpeg stream copy)
   - Mode **words** : timestamps mot par mot → analyse speech complète
   - Mode **segments** : timestamps par segments → conversion pseudo-mots
   - Mode **texte** : texte brut → fallback chat-only (analyse speech désactivée)
3. **Chat replay Twitch** (API v5 publique, pas d'auth) → pics d'engagement
4. **Speech analysis** (triggers, punchlines, densité) — si mode words/segments
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


## 2026-09-06 — Transcription GPU Modal (moteur swappable)

**Statut** : ✅ Déployé et testé en production (run GH Actions vert + artefacts commités)

### Fichiers créés
- `MODAL/transcribe.py` → service endpoint `/audio/transcriptions` (faster-whisper GPU)
- `MODAL/requirements.txt` → dépendances (référence)
- `MODAL/DEPLOYER.md` → guide déploiement/rotation de compte

### Ce qui a changé
- **Aucun** changement dans `f00b_vox.py` / `auto_detector.py`.
- La transcription passe par un endpoint OpenAI-compatible sur GPU Modal au lieu du CPU local.
- La config se fait dans `f00b_secrets.json` (`base_url` = URL Modal), jamais dans le code.

### Décision clé
- Clé premium NVIDIA = **analyse/copywriting** (pas transcription).
- Transcription = **Modal (Whisper medium)** — modèle swappable via config.
- Rotation de compte Modal possible sans toucher au code (crédits gratuits).


## 2026-09-06 — Orchestration Oracle via GitHub Actions

**Statut** : ✅ Orchestration validée — premier test de production réel réussi

### Fichiers créés/modifiés
- `.github/workflows/perturabo_transcribe.yml` → pipeline deploy→transcribe→score→commit
- `GUIDE_UTILISATION/16_ORCHESTRATION_GITHUB_ACTIONS.md` → doctrine des rôles
- `MODAL/DEPLOYER.md` → corrigé (déploiement via GH Actions, plus machine opérateur)

### Décision clé
- L'opérateur ne code pas, ne déploie pas, ne clique pas : il valide les Portes.
- L'Oracle (Cody) déclenche le workflow via l'API et suit les runs.
- Secrets injectés en aveugle (chiffrés libsodium), jamais commités.


## 2026-09-06 — Premier test de production réel (VOD aishahsofey)

**Statut** : ✅ SUCCESS — run GitHub Actions vert, artefacts commités dans ARCHIVUM.

### Résultat
- VOD : `https://www.twitch.tv/videos/2864600351` (aishahsofey, GTA V REACTIONS, 3h29)
- Transcript : `ARCHIVUM/montage/transcripts/v2864600351_transcript.json` (15 118 mots word-level)
- Candidats : `ARCHIVUM/montage/transcripts/v2864600351_candidats.json` (9 acceptés / 1 rejeté)

### Correctifs apportés au service Modal (leçons)
1. `requests==2.32.3` manquant → 500 (faster-whisper importe `requests` dans utils.py)
2. Image de base : `debian_slim` → `nvidia/cuda:12.4.0-runtime-ubuntu22.04` (libcublas.so.12 manquant → 500)
3. Préchargement du modèle au build (`.run_function`) + fallback CPU si CUDA absente
4. Endpoint durci : renvoie le traceback dans le corps du 500 (plus jamais aveugle)


## 2026-09-06 — Plan refonte VOX validé (architecture multi-capteurs)

**Statut** : PLAN VALIDÉ — non implémenté. Documenté dans `PLAN_REFONTE_VOX.md`.

### Diagnostic ayant motivé la refonte
- `score_candidates()` ne reçoit pas ARCHIVUM (4 params) : scoring syntaxique en dur.
- `intensity:0.9` constant (auto_detector l.380), jamais mesuré.
- Directive campagne absente du scoring ; F00B_VOX n'a AUCUN capteur dédié (vs F00A ~14).

### Cible
Tableau brut multi-capteurs → scoring → arbitrage premium (kimi-k3). Entonnoir 4 étages
(le premium ne voit que les survivants). Clause campagne complète en veto.

### Décisions
Directive campagne complète · clé premium = sémantique + arbitrage · full capteurs en entonnoir.
Partie Modal figée (succès).


## 2026-09-06 — P1 refonte VOX : filtre veto directive campagne

**Statut** : ✅ FAIT + poussé.

### Fichiers
- `CODEBASE/libs/campaign_veto.py` (nouveau) — contrat tableau brut + parse directive + veto.
- `CODEBASE/libs/auto_detector.py` — branchement veto dans `run_auto_detect` (étape 8b).

### Ce que fait P1
- plateforme non autorisée → `auto_rejected` (veto dur)
- exclusions (of_creator, onlyfans, bait/misinfo, negative_pr) → veto dur
- VOD hors cycle → warning (prolongation possible via annonce)

### Point d'attention
La VOD de test (2026-09-04) est HORS cycle campagne Aishah Sofey (7/20→7/31) :
warning, pas rejet. À confirmer côté Warsmith.


## 2026-09-06 — P2→P6 refonte VOX : capteurs + intensité réelle + premium

**Statut** : ✅ FAIT + poussé (test local validé). Run réel à confirmer.

### Livré
- `libs/vox_refonte.py` : capteurs émotes/vélocité/événements/lexical + `real_intensity()` + `build_raw_table()`.
- `libs/vox_premium.py` : arbitrage kimi-k3 (reframing + verdict).
- Patch `run_auto_detect` : intensité réelle → veto → premium ; produit `OUT/raw_table.json`.
- Workflow : injecte NVIDIA (clé + modèle kimi-k3).

### Point décisif
`signal_intensity` n'est plus la constante 0.9 (auto_detector l.380) : elle est calculée
par convergence de 4 signaux (emo 0.35 / vel 0.25 / evt 0.20 / hook 0.20). Fumée :
fenêtre riche=0.9, vide=0.1.


## 2026-09-06 — Capteurs audio + visuel (P4 phase 2)

**Statut** : ✅ créés + branchés (dégradation gracieuse). En attente clés Twitch pour clips.

### Fichiers
- `libs/audio_sensor.py` (rire/applaudissement, heuristique RMS+ZCR) — gratuit, fenêtres seulement.
- `libs/visual_sensor.py` (face OpenCV + cut ffmpeg) — gratuit.
- `vox_refonte.py` : colonnes `audio_laugh/applause` + `visual_face/cut` branchées.
- `auto_detector.py` : injecte `_audio_path` dans les candidats avant `build_raw_table`.
- workflow : `opencv-python-headless` ajouté.

### Reste → FAIT
Capteur clips communautaires = `libs/clips_heatmap.py` via **GraphQL public Twitch** (Client-ID web anonyme, zéro clé). Heatmap densité × vues + titres. Branché dans `build_raw_table` + `run_auto_detect`.


## 2026-09-06 — Test réel : découvertes + fixes (chat mort + ordre scoring)

**Statut** : ✅ Fix complété. Validation réelle sur données déjà transcrites (pas de re-transcription).

### Découvertes (le test réel a révélé)
1. **API v5 du chat Twitch = morte** (0 message) → le `intensity:0.9` d'origine était fictif.
   → `fetch_chat_replay` réécrit en **GraphQL public** (successeur, pagination par offset Int).
   → Validation : 2641 messages réels récupérés.
2. **Bug d'ordre** : `score_candidates` tournait AVANT `build_raw_table` → intensité réelle jamais consommée.
   → Réordonnancement : capteurs (8a) → scoring (8) → veto (8b) → premium (8c).
3. **campaign_veto** ne posait pas `status` sans veto (KeyError) → corrigé (toujours posé).

### Preuve
Intensité sur 9 candidats réels : **7 valeurs distinctes** (0.25→0.58) au lieu de 1 seule (0.9).

### Fix commits
fetch_chat GraphQL · réordonnancement · campaign_veto status · emote_signal (tout emote).


## 2026-09-06 — GO Warsmith + dé-saturation vélocité

**Statut** : ✅ Refonte VOX validée (GO) + calibrage vélocité corrigé.

### Fix post-GO
- `velocity_signal` : saturation à 1.0 partout → courbe douce `1 - exp(-ratio/4)` (discriminante).
- Nouveau `spike_signal` : burstiness (concentration temporelle 5s) — distinct de la vélocité.
- Pondération intensité : emo 0.30 · vel 0.15 · **spike 0.15** · evt 0.20 · hook 0.20.
- `chat_spike` dans le tableau brut = vrai spike (plus un doublon de vélocité).


## 2026-09-07 — Test RÉEL de détection bout-en-bout

**Statut** : ✅ Test réel complet (détection fraîche, pas re-scoring d'archive).

### Ce que le test réel a révélé (et pourquoi il valait mieux que la valisation hors-ligne)
- **Bug `tos_hits`** (`UnboundLocalError`) sur fenêtre sans mots → corrigé (commit `f57f43e`).
  La valisation hors-ligne sur l'archive ne l'aurait JAMAIS vu (les candidats frais créent des fenêtres sans texte).

### Résultats réels
- chat = 5 301 messages (GraphQL public, balayage homogène 80s).
- 642 speech peaks + 30 chat peaks → 10 candidats frais → 9 survivants (0 veto dur).
- `top_words` renseignés 7/9 (le premium a de quoi analyser).
- intensité réelle différenciée : 0.11 → 0.42.
- premium kimi-k3 : HTTP 200 OK (test direct), score réel discriminant (≠ neutre 5.0).


## 2026-09-07 — Injection premium finalisée (plomberie)

**Statut** : ✅ Injection `NVIDIA_NIM_API_KEY` faite (HTTP 204, libsodium, aveugle) + vérifiée.

### Détails
- Workflow `perturabo_transcribe.yml` : étape auto_detect référence bien `NVIDIA_NIM_API_KEY` + `NVIDIA_NIM_MODEL=moonshotai/kimi-k3`.
- Secret injecté dans GitHub Actions (idempotent PUT) → 204 No Content.
- Secrets GitHub présents : MODAL_TOKEN_ID, MODAL_TOKEN_SECRET, NVIDIA_NIM_API_KEY.
- Premium prouvé par test direct (kimi-k3 → HTTP 200, score discriminant).

### Reste (production)
Run workflow complet sur NOUVELLE VOD = validation finale de production. Le premium est prêt
(top_words → kimi-k3 → verdict ok/weak/skip).

## 2026-09-09 — Branche v2-live : la couche LIVE de VOX

**Statut** : ✅ Livrée (radar + session + gate hybride + board).

- `libs/chat_pulse.py` : radar IRC anonyme (justinfan, aucun token), vitesse chat /10s, baseline EMA 5 min, mots chauds 30s, clip pressure, warm-up 30s + cooldown 120s/chaîne, PING→PONG géré.
- `libs/helix_clipper.py` : get_stream_info + create_clip (TWITCH_TOKEN/TWITCH_CLIENT_ID en env — jamais de fichier).
- `f00b_vox_live.py` : orchestrateur — réutilise `compute_score` de f00b_vox.py (zéro fork du moteur), gate hybride (auto ≥ 8.5 + intensité ≥ 0.9), OUT : live_moments / candidats_live / scoring_live / gate_live / trail / helix_clips / live_status, tous crash-safe (écrits à chaque moment).
- `trail.json` au même schéma que VOD → F04/F06 ne voient aucune différence.
- Hérésie respectée : 0 dépendance pip ajoutée (requirements_f00b.txt annoté).

### Reste
- Session de calibration sur live réel (seuils radar par taille de chaîne).
- Kick (Pusher public) : prévu v2.1 (champ `kick_channels` déjà en place, non actif).

## 2026-09-10 — v2-live : scoring calibré + Salle de Contrôle + Garde de Fer

**Statut** : ✅ Livré (commit miroir `df573fc`+ · PERTURABO `0b67aad8ff` → maj suivante).

- **Garde de Fer** (`libs/campaign_gate.py` + `ARCHIVUM/campaign/live_campaigns.json`) :
  résolution chaîne → campagne au lancement, sessions mixtes refusées, verdicts marqués
  `campaign_eligible`/`campaign_id`/`campaign_state` (propagés artefacts + board).
  Workflow : input `mode_override` (auto/technical_test/campaign).
- **Scoring calibré** (`compute_score_live`) : critères alimentés par la force réelle
  du pic (ratio rate/baseline, hystérie mots chauds, clip_pressure, durée). Profil fixe
  ~9.88 supprimé — preuve session #3 : écart 0.0 → 3.25. Moteur VOD main intact.
- **Fix** : `write_status()` recevait `cfg` sans paramètre (crash garanti session #4)
  — signature corrigée, `cfg` passé aux 2 appels.
- **Board « Salle de Contrôle du Siège »** (`docs/index.html`) : palette IW
  (Boltgun/Leadbelcher/Shining Gold/noir + hazard), logo ⟨/⟩ SVG, carte du siège SVG
  (muraille pulsante par pression chat), Scoreur en direct (jauge or + détail critères
  + tampons), Manifeste des clips (liens Helix), file Warsmith, télémétrie lampes.
- **Données board** : `live_status.json` publie désormais `recent_scored` (critères
  détaillés) et `clips` (IDs/URLs Helix) à chaque tick ; refresh board 60 s.
