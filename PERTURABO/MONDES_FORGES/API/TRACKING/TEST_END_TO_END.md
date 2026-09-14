# TEST END-TO-END — Monde-Forge API

## Pré-requis
```bash
cp .env.example .env
# Remplir dans .env :
AI_GATEWAY_BASE_URL=...
AI_GATEWAY_API_KEY=...
GITHUB_TOKEN=...          # pour deploy automatique
RAPIDAPI_KEY=...          # optionnel, pour sentinel_rapid
```

## Installation
```bash
pip install -r ../../CORE/requirements.txt
```

## Siège complet
```bash
cd MONDES_FORGES/API/ORCHESTRATOR/CODEBASE
python orchestrator.py --enclenche
# Optionnel : hint de catégorie
python orchestrator.py --enclenche --hint "LinkedIn profile scraper"
```

## Flux attendu
```
T+00:00  SENTINEL scan RapidAPI + GitHub (20 min max)
T+00:20  TYRANT identifie la cible et la faille
         GATE 1 : Warsmith valide la cible (O/N)
T+00:25  BREACHER score + 20 angles d'attaque
         GATE 2 : Warsmith valide les angles (O/N)
T+00:30  FORGEWARD forge 20 Iron Warriors en parallèle
         GATE 3 : Warsmith valide les warriors (O/N)
T+00:45  HERALD génère 20 listings RapidAPI + README
         GATE 4 : Warsmith valide les listings (O/N)
T+00:55  GRAND COMPASS déploie sur GitHub + URLs Railway
         CAPTEURS initialisés
T+01:00  Siège terminé — 20 Iron Warriors en ligne
```

## Vérifications post-siège
```bash
# État du siège
python orchestrator.py --status

# Voir les URLs de deploy
cat fregates/F05_GRAND_COMPASS/OUT/deploy_results.json | python3 -m json.tool

# Monitoring quotidien (à planifier en cron)
python fregates/F06_CAPTEURS/CODEBASE/capteurs.py --scan --siege-id [ID]

# Mise à jour manuelle des abonnés RapidAPI
python fregates/F06_CAPTEURS/CODEBASE/capteurs.py --scan --siege-id [ID] \
  --manual-update '{"1":{"subscribers":5},"3":{"subscribers":12}}'

# Rapport de survie
python orchestrator.py --rapport
```

## Actions Warsmith post-deploy
1. Clique chaque URL Railway dans deploy_results.json pour finaliser le deploy
2. Publie chaque API sur RapidAPI avec le contenu de listing_rapidapi.md
3. Note le slug RapidAPI de chaque API dans le ledger F06
4. Programme le scan quotidien : cron ou tâche planifiée

## Reprise après interruption
```bash
python orchestrator.py --resume
```
Le système reprend selon le fleet_status dans liber_api.json.

## Structure des outputs
```
ARCHIVUM/targets/[siege_id]/ironwarriors/
  warrior_01/
    api.py              <- code FastAPI à déployer
    requirements.txt
    openapi.json        <- spec OpenAPI (pour agents IA)
    README.md           <- optimisé LLM
    listing_rapidapi.md <- texte de publication RapidAPI
    deploy.sh           <- one-liner Railway
    meta.json           <- métadonnées warrior

ARCHIVUM/ledgers/
  [siege_id]_ledger.json  <- tracking survie en temps réel

ARCHIVUM/rules/
  patterns_gagnants.md    <- doctrine enrichie à chaque siège
```