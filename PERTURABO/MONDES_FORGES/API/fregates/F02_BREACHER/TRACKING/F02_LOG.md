# F02_BREACHER — Journal de Mission — Monde-Forge API

> Le Briseur — Scoring de cible et identification des 20 angles
> Pipeline : raw_intel.json + ARCHIVUM/rules/ → scored_target.json

| Champ | Valeur |
|-------|--------|
| Frégate | F02_BREACHER |
| Rôle | Le Briseur — Scoring de cible et identification des 20 angles |
| Moteur | deepseek/deepseek-v4-flash via AI Gateway |
| IA | IRON — scoring + identification des angles d'attaque |

## Workflow

```
python breacher.py --prepare
# IRON lit iron_prompt.txt → produit scored_target.json
python breacher.py --finalize
```

## Détail

| Scoring | Poids |
|---------|-------|
| Popularité RapidAPI | 0.35 |
| Latence élevée (faille) | 0.25 |
| Wrappers GitHub actifs | 0.20 |
| Frustration pricing (reviews) | 0.20 |

## Historique des missions

*(Généré automatiquement par breacher.py lors des sièges)*
