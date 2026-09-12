# S03_LOG — Frégate FORGEWARD SHORT

> *Étanchéité absolue. Cette frégate ne communique que via liber_perturabo.json.*
> *Le fer qui forge le Short.*

---

## [INIT] S03_FORGEWARD SHORT — Structure créée

Frégate de forge de script/storyboard Short.
Produit un script de 30-60s avec loop hook, adapté au format de contenu identifié.

### Codebase (à coder)
- `forgeward_short.py` — Forge le script Short (prepare → IRON → finalize)
- `contracts_loader_short.py` — Charge iron_prompt_short + skeleton_checklist_short + anti_bullshit + shorts_doctrine + ARCHIVUM

### Spécificités Shorts
- Durée cible : 30-60s
- Loop hook obligatoire
- 6 formats de contenu (visual only, text on screen, voiceover, green screen, duet, image carousel)
- META_01 format Short (plus rapide, plus dense)
- Timing : ~1-2s par ligne (vs ~2.5s en Long)
- Pas de CTA "abonne-toi"

### Architecture hybride
Phase 1 (--prepare) : forgeward_short.py assemble le prompt (squelette + niche + contrats)
Phase 2 (IRON)      : Claude génère le script/storyboard Short
Phase 3 (--finalize): forgeward_short.py valide → check-in IW_CUSTOS

*Fer au-dedans, Fer au-dehors.*
