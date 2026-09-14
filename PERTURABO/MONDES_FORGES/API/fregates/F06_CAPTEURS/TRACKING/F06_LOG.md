# F06 CAPTEURS — TRACKING LOG

## Rôle
Surveillance post-siège quotidienne. Détecte patterns gagnants, alimente ARCHIVUM/rules/.

## Workflow
```
python capteurs.py --init --siege-id API-001
python capteurs.py --scan --siege-id API-001
python capteurs.py --report --siege-id API-001
python capteurs.py --scan --siege-id API-001 --manual-update '{"1":{"subscribers":15}}'
```

## Seuils
- deployed : état initial
- vivant   : >= 3 abonnés RapidAPI
- gagnant  : >= 10 abonnés RapidAPI
- mort     : 0 abonné après 30 jours

## Output
- ledgers/[siege_id]_ledger.json
- ARCHIVUM/rules/patterns_gagnants.md (couche froide enrichie)
- OUT/[siege_id]_report.json

## Note
Métriques RapidAPI via --manual-update avec chiffres du Provider Dashboard.