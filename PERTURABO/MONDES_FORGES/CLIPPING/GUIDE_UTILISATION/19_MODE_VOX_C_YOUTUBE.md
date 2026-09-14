# 19 — MODE VOX-C : ANALYSE YOUTUBE / TWITCH (F00C_VOX)

> *La plateforme sait déjà ce qui est viral. F00C lit cette mémoire.*

## Ce que c'est

**F00C_VOX** = la Voix des Plateformes. Là où F00B écoute le **chat Twitch**
(radar live) et analyse les VOD Twitch, F00C lit la **mémoire de la plateforme** :
heatmap d'attention (l'équivalent de la barre rouge YouTube, calculée depuis la
source), segments viraux et données brutes — sur :

- un **live YouTube en cours** (détection `is_live` automatique)
- une **vidéo YouTube finie** (un live fini est servi comme vidéo — même pipeline)
- une **VOD ou un live Twitch** (métadonnées GQL publiques)
- un **fichier local** (analyse média directe)

**Un seul manifeste** (`perturabo.voxc.v1`) pour les deux cas : l'Oracle reçoit
toujours la même structure, que la source soit un live en cours ou une vidéo finie.

## Emplacement

```
MONDES_FORGES/CLIPPING/F00_IRON_SENTINEL/F00C_VOX/
├── CODEBASE/f00c_vox.py            ← CLI principale
├── CODEBASE/tests/test_f00c_vox.py ← 8 tests hors-ligne
├── CODEBASE/requirements_f00c.txt  ← stdlib + numpy ; yt-dlp/ffmpeg système
├── IN/vox_c_input.example.json     ← format d'entrée documenté
├── OUT/live_analysis.json          ← manifeste produit
└── TRACKING/                       ← F00C_LOG.md + F00C_GATES.md
```

## Usage CLI

```bash
cd MONDES_FORGES/CLIPPING/F00_IRON_SENTINEL/F00C_VOX

# 1. Metadata seule (rapide, aucun téléchargement) — live OU vidéo
python3 CODEBASE/f00c_vox.py "https://www.youtube.com/watch?v=<VIDEO_ID>"
# → OUT/live_analysis.json (status: metadata_only)

# 2. Metadata + heatmap + pont PUR (schéma canonique)
python3 CODEBASE/f00c_vox.py "https://www.youtube.com/watch?v=<VIDEO_ID>" \
  --download-budget-seconds 600 --to-candidats --top 5
# → heatmap + segments + OUT/candidats.json (clé candidates)

# 3. Fichier local (heatmap directe, aucun réseau)
python3 CODEBASE/f00c_vox.py /chemin/clip.mp4 --out OUT/live_analysis.json

# 4. Twitch (VOD ou chaîne en live)
python3 CODEBASE/f00c_vox.py "https://www.twitch.tv/videos/<ID>"
python3 CODEBASE/f00c_vox.py "https://www.twitch.tv/<channel>"

# 5. Contrat découplé : métadonnées = URL YouTube, média = fichier local
python3 CODEBASE/f00c_vox.py "https://www.youtube.com/watch?v=<VIDEO_ID>" \
  --media-source /chemin/video.mp4 --to-candidats

# 6. Session autorisée (cookies burner — secret YT_COOKIES_BASE64 restauré en /tmp)
python3 CODEBASE/f00c_vox.py "https://www.youtube.com/watch?v=<VIDEO_ID>" \
  --download-budget-seconds 3600 --cookies-file /tmp/yt_cookies.txt --to-candidats
```

## Le mur anti-bot et l'escalier (Livraison A)

> Depuis un runner GitHub (IP datacenter), YouTube répond
> **« Sign in to confirm you're not a bot »** : c'est un mur **identitaire**, pas une
> panne de configuration. Aucun paramètre de budget ne le contourne.

`download_media` monte maintenant un **escalier à 3 marches** :

1. **`player_client=ios,mweb`** (gratuit, parfois suffisant — toujours essayé en premier) ;
2. **yt-dlp nu** (comportement courant de l'outil) ;
3. **`--cookies-file`** (session burner autorisée — la vraie clé).

Formats : **video-only 144p** (la heatmap réduit à 64×36, l'audio est inutile →
~30-60 Mo/h au lieu de Go). En cas d'échec complet : `metadata_only` — mais le
**garde-fou** transforme ce cas en **échec explicite** (CLI exit 2, workflow exit 1) :

> `Analyse fonctionnelle échouée : média non récupéré, heatmap absente ou aucun candidat produit.`

**Succès technique ≠ succès réel.** Un workflow vert n'a de valeur que si
`status: full` (ou si le média a été fourni via `--media-source`).

### La barre rouge et le webhook (Livraison B)

**`--fetch-replayed`** récupère la **barre rouge YouTube** (Most Replayed) via
`yt-dlp --dump-json` — **aucun média téléchargé** — et la stocke dans
`replayed_curve` du manifeste. Si elle est indisponible, `replayed_note`
explique pourquoi (jamais de silence).

La **fusion** (`fused_heatmap`) croise les deux mondes :

```
fused = 0.6 × attention_norm (capteur F00C) + 0.4 × replayed_norm (humains réels)
```

C'est le croisement le plus puissant du projet : ton capteur × le comportement
de millions de spectateurs. Sans barre rouge, dégradation propre
(`fused = attention_norm`, `replayed_applied: false`).

**`--webhook-url`** pousse le payload complet (contrat §4 du plan) vers la
**Salle de Guerre** avec l'en-tête `X-Siege-Token` (secret partagé,
défaut : env `SIEGE_WEBHOOK_TOKEN`). Le webhook ne bloque jamais le livrable
local en cas d'échec réseau.

```bash
python3 CODEBASE/f00c_vox.py "https://www.youtube.com/watch?v=<ID>" \
  --fetch-replayed --to-candidats \
  --webhook-url https://<salle-de-guerre>/hook
```

Récepteur de référence : `war_room/receiver.py` (repo kbkjhjhl) —
self-test, validation stricte du contrat, `GET /api/war-room` pour le dashboard.

### Cookies burner — protocole du Warsmith

1. Compte Google **burner** (jamais le compte de publication), profil navigateur dédié ;
2. Connexion YouTube → extension « Get cookies.txt LOCALLY » → export **Netscape** de youtube.com ;
3. `base64 -w0 cookies.txt` → coller dans le secret GitHub **`YT_COOKIES_BASE64`** ;
4. Le workflow restaure le secret dans `/tmp/yt_cookies.txt` (`umask 077`) et le **détruit en fin de job** ;
5. Rotation hebdomadaire, révocation immédiate si alerte. **Jamais dans le chat, un commit ou un log.**

## Via GitHub Actions (sans machine locale)

Actions → **« PERTURABO VOX-C ANALYSIS (F00C) »** → Run workflow :
`source_url` + `download_budget_seconds` (0 = metadata seule, 600 = 10 min
analysées). Gate L0 vérifie la source, l'artefact `voxc-analysis-*` contient
le manifeste. ⚠️ **Aucun run sans GO du Warsmith** (règle des journaux).

## Lire le manifeste (décision Oracle)

| Champ | Signification |
|---|---|
| `source.content_type` | `live_ongoing` ou `video` — l'état au moment de l'analyse |
| `metadata` | Titre, durée, vues, auteur, `is_live`, `playable` (données brutes) |
| `attention_heatmap[]` | Buckets chronologiques : `start_sec`, `end_sec`, `attention`, `attention_norm` (0→1) |
| `viral_segments[]` | Top pics espacés de ≥ 5 s, classés `rank` — **la matière première des angles** |
| `status` | `full` (tout est là) / `metadata_only` (relancer avec budget > 0) / `metadata_only_media_error` |

**Flux de décision** : heatmap + segments → pont `--to-candidats` → tronc PUR
(F04 copywriting, F06 montage). Les données brutes du manifeste servent à
justifier la décision Oracle, jamais à la remplacer.

---

## Le flow PUR complet depuis F00C

> **Point d'entrée : F00C (YouTube / Twitch / local).** Ensuite : le MÊME tronc
> que F00B. Voir aussi guides 13 (PUR direct), 14 (opérateur), 20 (note technique).

**Deux entrées, un tronc, une sortie.** F00C n'est plus un cul-de-sac : le flag
`--to-candidats` convertit `viral_segments` en `OUT/candidats.json` (schéma
canonique, clé `candidates`, `signal_type: "platform_heat"`).

```
YouTube / local : f00c_vox.py --to-candidats → OUT/candidats.json
    ↓
pur_adapter_direct → F04_COPYWRITER → pur_montage_pipeline (F06 inline)
    ↓
pack → ⛔ GATE Warsmith → EXPORT/ → OMNIS_WATCH
```

F01 / F02 / F03 sont **SKIPPÉS** (VOX a déjà détecté, scoré, sélectionné).

### CLI — pont vers le tronc

```bash
cd MONDES_FORGES/CLIPPING/F00_IRON_SENTINEL/F00C_VOX

python3 CODEBASE/f00c_vox.py "https://www.youtube.com/watch?v=<VIDEO_ID>" \
  --download-budget-seconds 600 \
  --to-candidats --top 5
# → OUT/live_analysis.json  (manifeste Oracle, inchangé)
# → OUT/candidats.json      (schéma canonique PUR)
```

### Chaînage GitHub Actions (aucun méga-workflow)

| Étape | Action |
|---|---|
| 1. Capteur | Actions → **« PERTURABO VOX-C ANALYSIS (F00C) »** (`to_candidats=true`, défaut) → artefact `voxc-candidats-*` |
| 2. Copywriting | Actions → **« F04_COPYWRITER PUR (VOX direct) »** : `candidats_path` = fichier de l'artefact F00C, `vod_url` = URL YouTube |
| 3. Montage | Actions → **`perturabo_montage.yml`** |
| 4. Gate + EXPORT | ⛔ validation Warsmith → copie dans `EXPORT/` |

Styles produits par le tronc (`--asset-mode`) : `ranking` / `blur` / `split` / `overlay_only` (PUR).

## Portes

Voir `TRACKING/F00C_GATES.md` (L0 source → L1 metadata → L2 heatmap → L3 segments).

## Doctrine (hérésies interdites)

- ❌ Jamais de VOD complète (`--download-sections` uniquement)
- ❌ Jamais de recompression (stream copy)
- ❌ Jamais de manifeste vide : même en metadata_only, l'Oracle reçoit un livrable
- ❌ Jamais de run CI sans GO explicite du Warsmith
- ❌ Jamais de **faux vert** : budget > 0 sans `status: full` → le job ÉCHOUE (garde-fou, Livraison A)
- ❌ Jamais de cookies de session dans un commit, un log ou le chat (secret GH uniquement, détruit en fin de job)

## Origine

Porté depuis **LACRIMAE `dev10-v3-live`** (`f00_live.py`, commit `d1b182c`,
8/8 tests verts) et adapté aux conventions F00B de PERTURABO. Dans LACRIMAE,
« F00C » désigne Motion Slow (interpolation) — sans rapport avec F00C_VOX.
