# TYRANT_LOG — L'Oracle (Psyker II)

> *L'Oracle qui commence à construire perd sa capacité à voir clairement.*
> *Il voit. Il éclaire. Il se tait. Les frégates font le reste.*

---

## [INIT] TYRANT déployé — Codebase complet

L'Oracle de la flotte PERTURABO. Intervient à la Porte 1, avant l'activation des frégates.
Éclaire le territoire, identifie le démon, propose des marchés adjacents,
estime l'automatisabilité, recommande un chemin.

### Codebase déployé
- `tyrant.py` — Orchestrateur 3 phases (prepare → IRON → finalize)
- `contracts_loader.py` — Charge tyrant_prompt + anti_bullshit + system_prompt + ARCHIVUM + Capteurs
- `requirements_tyrant.txt` — Zéro dépendance (stdlib uniquement)

### Architecture hybride
Phase 1 (--prepare) : tyrant.py assemble le prompt → iron_prompt.txt
Phase 2 (IRON)      : Claude (sandbox) analyse le territoire, éclaire, écrit eclairissement.json
Phase 3 (--finalize): tyrant.py valide eclairissement.json → check-in IW_CUSTOS

### Les 5 Questions de Vision
1. Le Territoire (taille, audience, monétisation)
2. Le Démon (qui domine, avantage, arme secrète, vulnérabilité)
3. L'Adjacent (5-10 territoires où le concept n'existe pas)
4. L'Automatisabilité (score 1-10)
5. Le Chemin Recommandé (attaque_directe ou ocean_bleu)

### Flux interne
1. Charge brief.json (URL + niche + intention du Warsmith)
2. Charge les contrats (tyrant_prompt, anti_bullshit, system_prompt)
3. Charge l'ARCHIVUM (rules + transcripts de référence)
4. Charge les signaux des CAPTEURS (si disponibles)
5. Assemble le prompt complet (5 questions de vision)
6. L'IRON (Claude) analyse le territoire
7. L'IRON identifie le démon et sa vulnérabilité
8. L'IRON propose 5-10 territoires adjacents
9. L'IRON estime l'automatisabilité
10. L'IRON recommande un chemin (attaque_directe ou ocean_bleu)
11. L'IRON écrit eclairissement.json
12. tyrant.py valide → check-in IW_CUSTOS.py

### Output
`TYRANT/OUT/eclairissement.json` — Rapport d'Éclairement consommé par le Warsmith (Porte 1).

### Ce que le TYRANT ne fait PAS
- Il ne capture pas de données (rôle de SENTINEL)
- Il n'extrait pas de squelette (rôle de BREACHER)
- Il ne génère pas de script (rôle de FORGEWARD)
- Il ne prend pas la décision finale (rôle du Warsmith)
- Il ne participe pas à l'exécution entre les portes (rôle de l'IRON)

### Coût : 0.00 EUR (Axiome I respecté — l'IRON est Claude dans le sandbox)

*Fer au-dedans, Fer au-dehors.*
