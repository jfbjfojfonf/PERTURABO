# ANTI-BULLSHIT — Monde-Forge API

## Principe

Toute règle, tout pattern, tout insight dans ce système doit être prouvé par des données réelles.
Pas d'intuitions. Pas de "généralement". Pas de "il est probable que".

## Filtres actifs

### Filtre 1 — Source obligatoire

Chaque affirmation stratégique doit citer sa source :
- `source: rapidapi_review` — review extraite de RapidAPI
- `source: github_issue` — issue GitHub ouverte ou fermée
- `source: github_search` — résultat de recherche code GitHub
- `source: archivum_rules` — pattern distillé depuis ARCHIVUM/rules/
- `source: ledger` — résultat d'un Iron Warrior déployé

Si la source est absente → le champ est `null`. Jamais une estimation présentée comme un fait.

### Filtre 2 — Chiffres prouvés

Un score de popularité vient de RapidAPI. Pas d'une estimation.
Une latence vient d'une mesure réelle. Pas d'une approximation.
Un nombre de repos GitHub vient d'une requête API. Pas d'un "beaucoup".

### Filtre 3 — Patterns ARCHIVUM uniquement

Les règles dans ARCHIVUM/rules/ sont les seuls patterns valides pour guider FORGEWARD.
Un pattern "semble fonctionner" n'entre pas dans rules/ tant qu'il n'a pas été validé par un ledger avec > 3 Iron Warriors survivants à 30 jours.

### Filtre 4 — Recommandation TYRANT

TYRANT ne recommande "SIEGEZ" que si :
- Score global ≥ 70/100
- Faille prouvée (pas supposée)
- Signal agents ≥ "moyen"
- Zone d'attaque prix identifiée

En dessous de ces seuils : "ATTENDEZ" ou "REORIENTEZ".

## Ce filtre s'applique à toutes les frégates

F01 → F06 : si une donnée ne peut pas être sourcée, elle est absente du liber.
Un liber incomplet est préférable à un liber contenant des inventions.
