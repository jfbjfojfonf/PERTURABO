# F05_LOG — Frégate GRAND_COMPASS

> *Étanchéité absolue. Cette frégate ne communique que via liber_perturabo.json.*
> *Le fer qui voit la carte entière.*

---

## [INIT] F05_GRAND_COMPASS déployée — Codebase complet

Frégate de cartographie de territoire de la IV Légion (Mode 2 — Lancement de Chaîne).
Niche Bending + Validation Océan Bleu + Stratégie de lancement.

### Codebase déployé
- `grand_compass.py` — Orchestrateur 3 phases (prepare → IRON → finalize)
- `web_search.py` — Recherche DuckDuckGo (gratuit, sans clé API) pour valider la concurrence
- `contracts_loader.py` — Charge system_prompt + anti_bullshit + iron_prompt + ARCHIVUM
- `requirements_f05.txt` — requests (pour DuckDuckGo)

### Architecture hybride
Phase 1 (--prepare) : grand_compass.py fait la recherche web + assemble le prompt
Phase 2 (IRON)      : Claude (sandbox) analyse, propose 8 marchés, valide top 3 océan bleu
Phase 3 (--finalize): grand_compass.py valide niche_report.json → check-in IW_CUSTOS

### Flux interne
1. Charge specimen.json (de F01_SENTINEL/OUT/)
2. Charge les contrats + ARCHIVUM (rules + transcripts de référence)
3. Recherche web préliminaire (DuckDuckGo — niche bending, chaînes anonymes)
4. Assemble le prompt complet (transcription + recherche web + règles)
5. L'IRON (Claude) identifie le concept + le format
6. L'IRON propose 8 marchés adjacents (niche bending)
7. L'IRON valide le top 3 en océan bleu (concurrence + monétisation + 5 idées de vidéos)
8. L'IRON recommande la meilleure niche
9. L'IRON écrit niche_report.json
10. grand_compass.py valide → check-in IW_CUSTOS.py

### Output
`F05_GRAND_COMPASS/OUT/niche_report.json` — rapport complet consommé par le Warsmith (Porte 2 Mode Chaîne).

### Coût : 0.00 EUR (Axiome I respecté — DuckDuckGo gratuit, l'IRON est Claude dans le sandbox)

*Fer au-dedans, Fer au-dehors.*
