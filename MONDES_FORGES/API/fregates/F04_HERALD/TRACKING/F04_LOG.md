# F04_HERALD — Journal de Mission — Monde-Forge API

> Le Héraut — Listings RapidAPI et README GitHub
> Pipeline : ironwarriors/ (20 dirs depuis F03) → listings/[id]/ × 20 (listing_rapidapi.md + README.md)

| Champ | Valeur |
|-------|--------|
| Frégate | F04_HERALD |
| Rôle | Le Héraut — Listings RapidAPI et README GitHub |
| Moteur | google/gemini-3.5-flash via AI Gateway |
| IA | IRON — rédaction listings + README LLM-optimized |

## Workflow

```
python herald.py --prepare
# IRON lit iron_prompt.txt → produit listings/ × 20
python herald.py --finalize
```

## Détail

| Output | Contenu |
|--------|---------|
| `listing_rapidapi.md` | Titre, description, tags, pricing (prêt à copier) |
| `README.md` | Doc LLM-optimized avec openapi.json référencé |

## Historique des missions

*(Généré automatiquement par herald.py lors des sièges)*
