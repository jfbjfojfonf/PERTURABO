# S02_LOG — Frégate BREACHER SHORT

> *Étanchéité absolue. Cette frégate ne communique que via liber_perturabo.json.*
> *Le fer qui brise le Short.*

---

## [INIT] S02_BREACHER SHORT — Structure créée

Frégate d'extraction du squelette viral d'un YouTube Short.
Utilise skeleton_checklist_short.json (6 éléments) + Gemini pour l'analyse vidéo.

### Codebase (à coder)
- `breacher_short.py` — Extrait le squelette Short (prepare → IRON → finalize)
- `contracts_loader_short.py` — Charge skeleton_checklist_short + iron_prompt_short + anti_bullshit + shorts_doctrine

### Squelette Short (6 éléments)
1. Visual Hook Frame (0-0.5s)
2. Verbal/Text Hook (0-3s)
3. Content Format (6 types)
4. Escalade/Rythme (3-50s)
5. Payoff (3-5s avant fin)
6. Loop Hook (dernière seconde)

### Architecture hybride
Phase 1 (--prepare) : breacher_short.py assemble le prompt (specimen + contrats)
Phase 2 (IRON)      : Claude + Gemini analyse la vidéo → extrait le squelette Short
Phase 3 (--finalize): breacher_short.py valide → check-in IW_CUSTOS

*Fer au-dedans, Fer au-dehors.*
