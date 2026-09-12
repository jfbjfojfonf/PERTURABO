# PERTURABO v2-live — F00C_VOX JOURNAL DE CAMPAGNE

> *Chaque entrée est immuable. Une fois écrite, elle ne s'efface pas.*

| Date | Source analysée | Statut | Segments | Run CI | Décision Warsmith |
|---|---|---|---|---|---|
| — | — | — | — | — | — |

## Entrées de mise en service

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
