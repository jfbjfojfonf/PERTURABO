# F02_BREACHER_LOG

## Role
Scorer les APIs candidates (F01 output), identifier la cible, generer 20 angles d'attaque.

## Workflow
1. --prepare : charge raw_intel.json de F01, ecrit breacher_context.json dans IN/
2. --iron    : Oracle score + genere 20 angles -> breacher_output.json dans OUT/
3. --finalize: valide schema, check-in IW_CUSTOS, affiche Gate 2

## Formule de scoring
score = popularite x 0.35 + latence_faille x 0.25 + wrappers x 0.20 + pricing_frustration x 0.20

## Output
{
  "cible_retenue": { "nom", "categorie", "score_total", "faille_principale" },
  "angles_attaque": [ { "id", "type", "description", "prix_suggere", "differenciateur" } x 20 ],
  "strategie_globale": "string"
}

## Statut
[x] Phase 6 -- Implementation complete
