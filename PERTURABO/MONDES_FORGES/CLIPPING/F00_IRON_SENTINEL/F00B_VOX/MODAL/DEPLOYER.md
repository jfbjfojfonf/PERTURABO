# MODAL — DEPLOYER (transcription GPU F00B_VOX)

> L'Oreille Absolue transcrit sur GPU Modal au lieu du CPU local.
>
> **IMPORTANT (mise à jour) :** le déploiement est désormais piloté par
> **GitHub Actions**, déclenché par l'**Oracle** — plus par la machine opérateur.
> Voir `GUIDE_UTILISATION/16_ORCHESTRATION_GITHUB_ACTIONS.md`.
> Ce fichier reste la référence bas-niveau du service `transcribe.py`.

---

## Ce que fait ce dossier

```
MONDES_FORGES/CLIPPING/F00_IRON_SENTINEL/F00B_VOX/MODAL/
├── transcribe.py      <- le service (endpoint /audio/transcriptions)
├── requirements.txt   <- deps (reference)
└── DEPLOYER.md        <- ce guide
```

## Déploiement AUTOMATIQUE (recommandé)

Aucune action manuelle. Le workflow `.github/workflows/perturabo_transcribe.yml`
exécute `modal deploy transcribe.py` sur le runner, en injectant
`MODAL_TOKEN_ID` + `MODAL_TOKEN_SECRET` depuis les secrets GitHub.

Déclenchement = l'Oracle (Cody) via l'API GitHub. L'opérateur ne déploie pas.

## Déploiement MANUEL (débug uniquement)

```bash
pip install modal
modal token set --token-id <ID> --token-secret <SECRET>
cd MONDES_FORGES/CLIPPING/F00_IRON_SENTINEL/F00B_VOX/MODAL
modal deploy transcribe.py
# -> URL: https://<workspace>--perturabo-whisper.modal.run
```

## Contrat de l'endpoint

Le service expose `POST /audio/transcriptions` (multipart/form-data) et renvoie
du word-level : `{"words": [{"word","start","end"}, ...], "text", "language"}`.
C'est le format "Case 1" que `auto_detector.py` privilégie pour le scoring.

## Modèle par défaut

`medium` (équilibre vitesse/qualité), GPU T4, `vad_filter=True`.
Changer via `WHISPER_MODEL=large-v3 modal deploy transcribe.py`.

## Image de base & correctifs (leçons du 1er test)

- Image de base : **`nvidia/cuda:12.4.0-runtime-ubuntu22.04`** (embarque `libcublas.so.12`). Ne PAS repasser sur `debian_slim`.
- Dépendance obligatoire : **`requests==2.32.3`** (faster-whisper l'importe). Sans elle → 500.
- Le modèle est **préchargé au build** (`.run_function(_download_model)`) ; fallback CPU si CUDA absente.
- Endpoint durci : en cas d'erreur, le 500 renvoie le traceback dans le corps (`{"error", "trace"}`).

## Aucun secret dans ce dossier

Le token Modal vit dans les secrets GitHub + env. Jamais committé.
