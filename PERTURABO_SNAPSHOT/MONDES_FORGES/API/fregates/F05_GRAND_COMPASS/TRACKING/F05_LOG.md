# F05 GRAND COMPASS — TRACKING LOG

## Rôle
Deploy automatique des Iron Warriors : création repos GitHub + push code + génération URLs Railway/Render.

## Workflow
```
python grand_compass.py --prepare   -> compass_config.json (plan deploy)
python grand_compass.py --iron      -> deploy_results.json (GitHub repos créés, fichiers pushés)
python grand_compass.py --finalize  -> URLs dans liber_api.json, F06 CAPTEURS initialisé
```

## Dépendances
- F03_FORGEWARD/OUT/warriors.json
- ARCHIVUM/targets/[siege_id]/ironwarriors/ (fichiers matérialisés par F03+F04)
- GITHUB_TOKEN dans .env (push automatique)

## Output
- deploy_results.json : warrior_id, github_url, railway_deploy_url, render_deploy_url
- liber_api.json f05.deployed_urls mis à jour

## Note
Railway/Render deploy final nécessite un clic humain sur les URLs générées.
Push GitHub entièrement automatique si GITHUB_TOKEN défini.