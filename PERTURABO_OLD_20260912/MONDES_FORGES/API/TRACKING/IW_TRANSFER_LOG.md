# IW_TRANSFER_LOG — Journal des Transferts Inter-Frégates MONDE-FORGE API

> Log de tous les transferts de fichiers entre frégates.
> Chaque entrée : source, destination, hash MD5, timestamp, statut.
> Géré automatiquement par `IW_CUSTOS.py`. Ne pas modifier manuellement.

---

## Transferts attendus par siège

| Ordre | Source | Destination | Fichier | Déclencheur |
|-------|--------|-------------|---------|-------------|
| 1 | TYRANT/OUT/ | F01_SENTINEL/IN/ | brief.json | Gate 1 validée |
| 2 | F01_SENTINEL/OUT/ | F02_BREACHER/IN/ | raw_intel.json | IW_CUSTOS check-in F01 |
| 3 | F02_BREACHER/OUT/ | F03_FORGEWARD/IN/ | scored_target.json | IW_CUSTOS check-in F02 |
| 4 | F02_BREACHER/OUT/ | F05_GRAND_COMPASS/IN/ | scored_target.json | IW_CUSTOS check-in F02 |
| 5 | F03_FORGEWARD/OUT/ | F04_HERALD/IN/ | ironwarriors/ (20 dirs) | IW_CUSTOS check-in F03 |
| 6 | F04_HERALD/OUT/ | SHARED/OUT/ | listings/ | IW_CUSTOS check-in F04 |
| 7 | F05_GRAND_COMPASS/OUT/ | ARCHIVUM/markets/ | blue_ocean_report.json | IW_CUSTOS check-in F05 |
| 8 | ARCHIVUM/ledgers/ | F06_CAPTEURS/IN/ | deployed_urls.json | Gate 4 validée |

---

## Historique des transferts exécutés

| TIMESTAMP | SOURCE | DEST | MD5 | STATUS |
|-----------|--------|------|-----|--------|
| — | — | — | — | En attente de premier siège |
