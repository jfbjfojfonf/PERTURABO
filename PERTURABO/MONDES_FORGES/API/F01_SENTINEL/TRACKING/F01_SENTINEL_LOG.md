# F01_SENTINEL_LOG

## Role
Renseignement multi-source : RapidAPI + GitHub + Web.
Produit raw_intel.json dans ARCHIVUM/targets/[siege_id]/

## Modules
- sentinel_web.py   : Jina Reader (fetch URL -> markdown)
- sentinel_gh.py    : GitHub API (wrappers, stars, code search)
- sentinel_rapid.py : Scrape RapidAPI via Jina Reader
- sentinel.py       : Orchestrateur 3 modes

## Workflow
1. --prepare : lit liber, genere sentinel_config.json dans IN/
2. --run     : lance les 3 modules, sauvegarde raw_intel_draft.json dans OUT/
3. --finalize: Oracle parse le brut -> raw_intel.json dans ARCHIVUM/targets/

## Output
ARCHIVUM/targets/[siege_id]/raw_intel.json
{ "apis_candidates": [...], "signal_global": "string" }

## Statut
[x] Phase 5 -- Implementation complete
