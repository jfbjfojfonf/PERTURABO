# F02_LOG — Frégate BREACHER

> *Étanchéité absolue. Cette frégate ne communique que via liber_perturabo.json.*
> *Le fer qui voit les fractures.*

---

## [INIT] F02_BREACHER déployée — Codebase complet

Frégate de dissection de la IV Légion. Extrait le squelette viral du specimen.
Architecture hybride : breacher.py prépare le prompt, l'IRON (Claude sandbox) exécute l'analyse.

### Codebase déployé
- `breacher.py` — Orchestrateur (prepare → IRON → finalize)
- `contracts_loader.py` — Charge skeleton_checklist.json + anti_bullshit.md + iron_prompt.md + ARCHIVUM rules
- `requirements_f02.txt` — Zéro dépendance IA (stdlib uniquement)

### Architecture hybride
Phase 1 (--prepare) : breacher.py assemble le prompt → iron_prompt.txt
Phase 2 (IRON)      : Claude (sandbox) lit le prompt, analyse, écrit skeleton.json
Phase 3 (--finalize): breacher.py valide skeleton.json → check-in IW_CUSTOS

### Flux interne
1. Charge specimen.json (de F01_SENTINEL/OUT/)
2. Charge les contrats (skeleton_checklist, anti_bullshit, iron_prompt)
3. Charge l'ARCHIVUM (rules/ + transcripts/ de référence)
4. Assemble le prompt complet → iron_prompt.txt
5. L'IRON (Claude) analyse la transcription avec la checklist
6. L'IRON extrait le squelette : Hook, Promise, Rehook_1, Rehook_2, Body_Structure, Payoff, CTA
7. L'IRON écrit skeleton.json
8. breacher.py valide le format JSON (7 éléments + champs)
9. Check-in IW_CUSTOS.py --frigate F02

### Output
`F02_BREACHER/OUT/skeleton.json` — squelette viral structuré consommé par F03_FORGEWARD.

### Coût : 0.00 EUR (Axiome I respecté — l'IRON est Claude dans le sandbox, pas une API payante)

*Fer au-dedans, Fer au-dehors.*
