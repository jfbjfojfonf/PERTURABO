# Mode PUR — Transcription GPU via Modal (F00B_VOX)

> Pourquoi ce guide : F00B_VOX (l'Oreille Absolue) transcrit l'audio des VOD Twitch.
> La transcription locale (CPU) est possible mais LENTE (~1h+ pour 105 min).
> A la place, on route la transcription vers un service Whisper sur GPU Modal.

---

## Le principe (0 modification de f00b_vox)

`auto_detector.PremiumTranscriber` envoie deja vers `{base_url}/audio/transcriptions`
un multipart (modèle + language + fichier), et attend en retour du word-level
(`words[]` avec start/end) OU `segments[]` OU `text`.

Modal expose exactement cet endpoint. On change juste `base_url` dans
`f00b_secrets.json` — le code de PERTURABO ne bouge pas.

## Architecture

```
VOD Twitch (aishahsofey)
   -> F00B_VOX: yt-dlp + ffmpeg -> chunk_XXX.m4a (audio seul)
   -> POST {base_url}/audio/transcriptions
   -> Modal: faster-whisper <model> sur GPU (T4)
   -> retour words[] word-level
   -> scoring multicritere + candidats.json (inchangé)
```

## Ce qui est sur GitHub (versionné, sans secret)

```
MONDES_FORGES/CLIPPING/F00_IRON_SENTINEL/F00B_VOX/MODAL/
├── transcribe.py      <- le service (endpoint /audio/transcriptions)
├── requirements.txt   <- deps (reference)
└── DEPLOYER.md        <- guide 1-commande pour deployer/redployer
```

## Ce qui N'EST PAS sur GitHub (local a l'operateur)

- Le **token Modal** (`MODAL_TOKEN`) — env var uniquement.
- `f00b_secrets.json` (gitignored) avec `base_url` pointant vers son deploiement.

## Déploiement — AUTOMATISÉ (ne plus faire à la main)

> ⚠️ Le déploiement est piloté par **GitHub Actions** déclenché par l'**Oracle**.
> Voir `16_ORCHESTRATION_GITHUB_ACTIONS.md`. Le mode manuel ci-dessous ne sert qu'au debug.

### Rappel manuel (debug uniquement)

```bash
pip install modal
modal setup            # ou: modal token set --token-id <ID> --token-secret <SECRET>
cd MONDES_FORGES/CLIPPING/F00_IRON_SENTINEL/F00B_VOX/MODAL
modal deploy transcribe.py
# -> URL: https://<workspace>--perturabo-whisper.modal.run
```

Puis editer `f00b_secrets.json` :

```json
{
  "env_var_name": "MODAL_TOKEN",
  "model_id": "medium",
  "provider": "other",
  "base_url": "https://<workspace>--perturabo-whisper.modal.run",
  "language": "en"
}
```

et exporter : `export MODAL_TOKEN="<token-secret>"`

## Choix du modèle

| Modèle | Vitesse | Qualité | Usage |
|---|---|---|---|
| `base` | très rapide | basse | test rapide |
| `medium` | rapide (GPU) | bonne | **défaut** (équilibre) |
| `large-v3` | ~1-2x real-time | excellente | production exigeante |

`medium` sur GPU T4 transcrit ~105 min en quelques minutes (vs ~1h45 en CPU local).

## Correctifs appliqués (leçons du 1er test)

| Problème | Fix |
|---|---|
| `ModuleNotFoundError: requests` → 500 | dépendance `requests==2.32.3` dans l'image |
| `RuntimeError: libcublas.so.12 is not found` → 500 | image de base `nvidia/cuda:12.4.0-runtime-ubuntu22.04` |
| modèle chargé au 1er appel (froid) | préchargé au build + fallback CPU |
| 500 muet | le endpoint renvoie le traceback dans le corps |

## Rotation de compte (credits gratuits)

Les credits gratuits Modal (~$1) s'épuisent. Pour repartir :
1. Nouveau compte Modal -> nouveaux credits gratuits.
2. Re-deployer `transcribe.py` (le code ne change JAMAIS).
3. Re-pointer `base_url` dans `f00b_secrets.json`.

Le code du service et ce guide restent identiques sur GitHub : seule l'URL du
deploiement change dans la config locale de l'operateur.

## Budget

105 min d'audio sur `medium` (T4) ~ quelques centimes -> bien sous les $1 gratuits.
Le service active `vad_filter=True` (ignore silences/musique) — utile pour les VOD
Twitch dont l'audio est partiellement mute (segments "index-muted").

> Limite de responsabilite : PERTURABO decrit et ordonnance ; Modal ne fait QUE
> la transcription de l'audio. Aucune donnee n'est stockee persistante (temp file
> supprime apres chaque requête).
