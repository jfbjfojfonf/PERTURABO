# S04_LOG — Frégate HERALD SHORT

> *Étanchéité absolue. Cette frégate ne communique que via liber_perturabo.json.*
> *Le fer qui forge la première frame.*

---

## [INIT] S04_HERALD SHORT — Structure créée

Frégate de design de la première frame d'un Short.
Les Shorts n'ont pas de thumbnail personnalisée — YouTube prend une frame du vidéo.
S04 designe ce que le spectateur voit avant de swiper.

### Codebase (à coder)
- `herald_short.py` — Design first frame (prepare → IRON → finalize)
- `contracts_loader_short.py` — Charge iron_prompt_short + anti_bullshit + shorts_doctrine + ARCHIVUM

### Spécificités Shorts
- Pas de thumbnail — c'est la première frame du vidéo qui compte
- Doit stopper le scroll (contraste élevé, mouvement, émotion)
- Lisible à la taille d'un ongle sur mobile
- Génère un concept de première frame via image_generator

### Architecture hybride
Phase 1 (--prepare) : herald_short.py assemble le prompt (specimen + contrats)
Phase 2 (IRON)      : Claude analyse + génère le concept de first frame
Phase 3 (--finalize): herald_short.py valide → check-in IW_CUSTOS

*Fer au-dedans, Fer au-dehors.*
