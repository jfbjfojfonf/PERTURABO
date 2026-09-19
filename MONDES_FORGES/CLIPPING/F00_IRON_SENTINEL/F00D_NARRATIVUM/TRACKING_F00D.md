# F00D_NARRATIVUM — Journal de session

## [2026-09-19] Session Aishah Sofey — gate F00B appliqué → 5 partitions blur → GATE F00D

- **Gate F00B** (Warsmith, 16:44 UTC) : 5 candidats approuvés (`62ac79ed87`,
  `1d3c465c61`, `4bdc43d3a1`, `fe6982e55c`, `b4a1cf9305`), tous `mixed`, scores
  9.7 → 8.57. Verdict enregistré : `F00B_VOX/IN/gate_decisions.json` +
  archivage `ARCHIVUM/montage/transcripts/v2873615032_gate_verdict.json`.
- **Extraction média** (règle d'or : jamais la VOD entière) : 5 tranches audio
  via `yt-dlp --download-sections` (+ `--force-keyframes-at-cuts`) →
  `F00D_NARRATIVUM/WORK/media/asf_c{1..5}.m4a` (~950 Ko / 60 s, 490 Ko / 30 s).
- **Inputs F00D** : `IN/asf_c{1..5}_input.json` (candidate + segment_media +
  constraints style=blur, youtube_shorts, us_young_english).
- **Échecs puis fixes (2 itérations)** :
  1. Première passe depuis le mauvais dossier de travail → chemins médias non
     résolus → climax fallback (55 % de la durée partout). Leçon : exécuter le
     directeur depuis la RACINE du dépôt (chemins d'input racine-relative).
  2. Deuxième passe : analyse audio réelle → saturation (48-65u > plafond 55u,
     jump cuts 10-15 > cap 8). Cause : seuil de silence 250 ms comptant les
     micro-pauses de conversation. Deux correctifs :
     - **Budget** (`caviar_budget.json`) : `silence_threshold_ms` 250 → 400
       (le calibrage appartient au Budget, source de vérité) ;
     - **Arbitrage composeur** (`caviar_director.py`) : le composeur VIT dans
       le budget — jump cuts tronqués au cap en gardant les silences les plus
       LONGS, puis retrait du moins long / des punch-ins tardifs si le plafond
       déborde encore. La politique `refuse_to_emit` reste la DERNIÈRE défense.
     - Tests : self-test OK + 10/10 pytest verts après patch.
- **Résultat final : 5/5 partitions `caviar.v1` style `blur` émises**
  (`OUT/caviar_manifest_asf_c{1..5}.json`), budget respecté partout :

| Clip | Candidat (gate F00B) | Climax réel | Resolution | Trims | broll_blur (panneaux) | Punch-ins | Budget |
|---|---|---|---|---|---|---|---|
| asf_c1 | 62ac79ed87 (9.7) | 12.5 s | 48 s | 2 | 15 / 30 s | 3 | 52/55u |
| asf_c2 | 1d3c465c61 (9.65) | 6.05 s | 48 s | 4 | 15 / 30 s | 3 | 54/55u |
| asf_c3 | 4bdc43d3a1 (9.59) | 4.7 s | 24 s | 8 | 7.5 s | 3 | 46/55u |
| asf_c4 | fe6982e55c (9.54) | 13.05 s | 48 s | 0 | 15 / 30 s | 3 | 50/55u |
| asf_c5 | b4a1cf9305 (8.57) | 3.45 s | 48 s | 5 | 15 / 30 s | 3 | 55/55u |

- Trio inséparable respecté (broll_blur + flash entrée + SFX impact, audio
  streamer MAINTENU), smash_audio (-12 dB) posé sur le climax réel de chaque
  clip, overlay placeholder (texte F04 à venir).
- **GATE F00D** : partitions soumises à l'opérateur. Émotion des panneaux blur
  à qualifier à ce gate (champ `emotion_requested` = « à qualifier »).
  Étape suivante après validation : **F04** (copywriting kimi-k3, titres +
  overlay + métadonnées), puis F06 → F05 → EXPORT.

## Leçons F00D (reprises dans `_PIEGES_APPRIS`)

- Toujours exécuter `caviar_director.py` depuis la racine du dépôt : les chemins
  `segment_media` des inputs sont racine-relatifs.
- Le Budget d'Attention est la source de vérité du calibrage — un paramètre de
  détection se règle là, jamais dans le code du composeur.
- Un candidat validé au gate F00B mérite une partition : le composeur arbitre
  (meilleurs événements dans le budget) au lieu de refuser ; refuser reste
  réservé au minimum vital non atteignable.
