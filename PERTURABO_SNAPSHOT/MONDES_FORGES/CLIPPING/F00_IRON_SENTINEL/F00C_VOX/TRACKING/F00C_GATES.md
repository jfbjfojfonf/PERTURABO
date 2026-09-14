# PERTURABO v2-live — F00C_VOX GATES

## Portes d'analyse

| Gate | Nom | Condition de passage |
|---|---|---|
| L0 | SOURCE | La référence est résolue : local, YouTube (ID extrait) ou Twitch (VOD ou chaîne). Sinon : échec bloquant. |
| L1 | METADATA | Métadonnées plateforme lues (page watch YouTube publique ou GQL Twitch). `playable` / `is_live` renseignés. |
| L2 | HEATMAP | Média local disponible (chemin direct ou tranche yt-dlp `*0-<budget>`) → heatmap d'attention complète. Sans média : dégradation metadata_only, jamais d'échec. |
| L3 | SEGMENTS | `top_viral_segments` retourne ≥ 1 pic espacé de ≥ 5 s (hors heatmap plate). |
| L4 | CANDIDATS | `--to-candidats` écrit `OUT/candidats.json` (schéma canonique). 0 segment → fichier vide + WARNING, le tronc refuse de continuer en silence. |

## Statuts du manifeste (`perturabo.voxc.v1`)

| Statut | Signification | Action Oracle |
|---|---|---|
| `full` | Metadata + heatmap + segments | Décision possible : heatmap, segments viraux, raw_data |
| `metadata_only` | Metadata seule (pas de yt-dlp ou budget 0) | Relancer avec `download_budget_seconds > 0` si heatmap voulue |
| `metadata_only_media_error` | Metadata OK mais heatmap en erreur | Lire `media_error` ; re-tenter ou changer de tranche |

## Règles immuables

1. Aucun run CI réel (dispatch, minutes Actions) sans GO explicite du Warsmith.
2. La heatmap vit sur le média local — elle n'appelle jamais le réseau.
3. Un manifeste est toujours écrit : l'Oracle reçoit un livrable même dégradé.
