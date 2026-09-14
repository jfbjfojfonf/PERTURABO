# Orchestration via GitHub Actions (F00B_VOX — rôle de l'Oracle)

> Ce guide remplace la procedure manuelle. Le déploiement Modal et la transcription
> sont désormais pilotés par GitHub Actions, déclenchés par l'ORACLE (Cody) — pas
> par l'opérateur.

---

## Rôle des acteurs (doctrine verrouillée)

| Acteur | Ce qu'il fait | Ce qu'il NE fait PAS |
|---|---|---|
| **Oracle (Cody)** | Déclenche le workflow via l'API GitHub, injecte les secrets, suit les Portes | Ne code pas, ne valide pas les Portes humaines |
| **GitHub Actions** | Déploie Modal, télécharge l'audio, transcrit, score, commit | Ne décide pas des angles |
| **Opérateur (Warsmith)** | Valide UNIQUEMENT les Portes (gate_verdict.json) | Ne code pas, ne clique pas, ne déploie pas |

## Flux complet

```
Oracle (Cody)
   -> POST /actions/workflows/{id}/dispatches   (déclenchement API, pas de clic)
GitHub Actions (ubuntu-latest : Docker + ffmpeg)
   1. modal deploy transcribe.py  -> Modal GPU (medium)
   2. écrit f00b_secrets.json -> base_url = URL Modal
   3. écrit vox_input.json
   4. python f00b_vox.py auto_detect  (download audio -> Modal transcribe -> scoring)
   5. commit transcript.json + candidats.json -> ARCHIVUM/montage/transcripts/
Oracle
   -> surveille le run, remonte les Portes à l'opérateur
Opérateur
   -> valide gate_verdict.json (seul point humain)
```

## Secrets (jamais dans le repo)

| Secret GitHub | Usage | Injecté par |
|---|---|---|
| `MODAL_TOKEN_ID` | déploiement Modal | Oracle (chiffré avec la clé publique du repo) |
| `MODAL_TOKEN_SECRET` | déploiement Modal | Oracle |
| `NVIDIA_NIM_API_KEY` | copywriting/Oracle (analyse transcripts) | Oracle |

L'Oracle reçoit les valeurs via le collecteur CodeWords, les lit depuis `os.environ`
(côté serveur), les chiffre avec la clé publique libsodium du repo, puis les
envoie via `PUT /actions/secrets/...`. Il ne les lit JAMAIS en clair.

## Workflow

Fichier : `.github/workflows/perturabo_transcribe.yml`

Déclencheur : `workflow_dispatch` UNIQUEMENT (pas de push) — la Porte de
déclenchement appartient à l'Oracle.

Inputs (non-secrets) : `vod_url`, `nb_clips`, `market`, `platform`.

## Rotation de compte Modal (crédits gratuits)

1. Nouveau compte Modal -> nouveaux tokens (Token ID + Secret).
2. L'Oracle re-injecte les secrets via le collecteur (étapes blind).
3. Le workflow `modal deploy` redéploie automatiquement — AUCUNE modification de code.

Le code (`MODAL/transcribe.py`) et ce guide ne changent JAMAIS entre les comptes.
