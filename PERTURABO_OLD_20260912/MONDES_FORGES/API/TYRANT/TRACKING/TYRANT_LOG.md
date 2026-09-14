# TYRANT_LOG — Frégate TYRANT

## Rôle
Identifier le démon RapidAPI dominant dans une catégorie, évaluer sa vulnérabilité,
proposer 20 angles d'attaque pour les Iron Warriors.

## Moteur
Oracle : anthropic/claude-sonnet-4.6 via CORE/ai_gateway.py

## Workflow
1. --prepare : contracts_loader assemble contexte → iron_prompt.txt dans IN/
2. --iron    : call_oracle("TYRANT", prompt) → tyrant_output.json dans OUT/
3. --finalize: valide JSON schema, check-in IW_CUSTOS, affiche Gate 1

## Schéma tyrant_output.json
{
  "cible": { "nom", "categorie", "url_rapidapi", "score_total" },
  "demon": { "nom", "popularite_score", "latence_ms", "pricing_frustration" },
  "vulnerabilite": { "type", "detail" },
  "angles_attaque": [ { "id", "type", "description", "prix_suggere" } x 20 ],
  "recommandation": "string — directive Warsmith"
}

## Dépendances
- CORE/ai_gateway.py
- MONDES_FORGES/API/CONTRACTS/tyrant_prompt.md
- MONDES_FORGES/API/ARCHIVUM/rules/ (couche froide)
- MONDES_FORGES/API/ARCHIVUM/targets/ (couche chaude, optionnel)
- MONDES_FORGES/API/IW_CUSTOS.py

## Statut
[x] Phase 4 — Implémentation complète
