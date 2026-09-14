# F03_FORGEWARD — Journal de Mission — Monde-Forge API

> La Forge — Production des 20 Iron Warriors
> Pipeline : scored_target.json + ARCHIVUM/templates/ → ironwarriors/[id]/ × 20 (api.py + openapi.json + requirements.txt + deploy.sh)

| Champ | Valeur |
|-------|--------|
| Frégate | F03_FORGEWARD |
| Rôle | La Forge — Production des 20 Iron Warriors |
| Moteur | anthropic/claude-sonnet-4.6 via AI Gateway |
| IA | IRON — génération code FastAPI + spec OpenAPI × 20 en parallèle |

## Workflow

```
python forgeward.py --prepare
# IRON lit iron_prompt.txt → produit ironwarriors/ × 20
python forgeward.py --finalize
```

## Détail

| Angle | Variante |
|-------|---------|
| Prix | 5 tiers différents |
| Endpoint | Focus différents selon cible |
| Vitesse | async ultra-rapide vs standard |
| Format | JSON pur / JSON+CSV / JSON+résumé |
| Niche | e-commerce / recrutement / sales / etc. |

## Historique des missions

*(Généré automatiquement par forgeward.py lors des sièges)*
