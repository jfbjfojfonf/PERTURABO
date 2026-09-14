# F01_SENTINEL — Journal de Mission — Monde-Forge API

> Le Renseignement — Collecte multi-source
> Pipeline : Catégorie RapidAPI (string) → raw_intel.json

| Champ | Valeur |
|-------|--------|
| Frégate | F01_SENTINEL |
| Rôle | Le Renseignement — Collecte multi-source |
| Moteur | RapidAPI scrape + GitHub API + Jina Reader |
| IA | Aucune — collecte brute uniquement |

## Workflow

```
python sentinel.py --run --categorie "LinkedIn Scraper"
# Pas d'IRON — collecte directe via modules
python sentinel.py --finalize
```

## Détail

| Module | Source | Output |
|--------|--------|--------|
| `sentinel_rapid` | RapidAPI listings | pricing, latence, reviews, popularité, endpoints |
| `sentinel_gh` | GitHub API search/code | wrappers actifs, étoiles, issues ouvertes |
| `sentinel_web` | Jina Reader | docs, articles, comparatifs |

## Historique des missions

*(Généré automatiquement par sentinel.py lors des sièges)*
