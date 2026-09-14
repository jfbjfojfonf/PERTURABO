# F03_LOG — Frégate FORGEWARD

> *Étanchéité absolue. Cette frégate ne communique que via liber_perturabo.json.*
> *Le fer qui forge l'arme.*

---

## [INIT] F03_FORGEWARD déployée — Codebase complet

Frégate de génération de script de la IV Légion. Forge un script original
au format META_01 (compatible CRUSADER/SANCTORUM/DORN) à partir du squelette viral.

### Codebase déployé
- `forgeward.py` — Orchestrateur 3 phases (prepare → IRON → finalize)
- `contracts_loader.py` — Charge system_prompt + anti_bullshit + iron_prompt + ARCHIVUM
- `requirements_f03.txt` — Zéro dépendance IA (stdlib uniquement)

### Architecture hybride
Phase 1 (--prepare) : forgeward.py assemble le prompt → iron_prompt.txt
Phase 2 (IRON)      : Claude (sandbox) génère le script + timing + métadonnées → script.json
Phase 3 (--finalize): forgeward.py valide + génère les exports → check-in IW_CUSTOS

### Compatibilité META_01 + META_02
- Script au format balisé : [ACCROCHE], [DÉVELOPPEMENT], [CHUTE/CTA]
- [mots_forts] entre crochets pour surlignage visuel
- `...` pour les pauses respiratoires
- Max 12 mots par phrase, 1 idée par ligne
- Métadonnées : titre (45 chars, 1 emoji), 3 hashtags, description 4 blocs (bloc 2 fixe)
- Timing par ligne : start/end estimés (~2.5s/ligne)
- timing.json exporté pour calage visuel (convention MM_SS_mmm.png)

### Outputs
- `script.json` — script structuré + métadonnées + timing par ligne
- `script_raw.txt` — format META_01 pour voix off → SANCTORUM
- `timing.json` — segments avec start/end pour META_02 / DORN / CRUSADER
- `metadata.txt` — titre + hashtags + description prêts à copier-coller YouTube Studio

### Anti-décalage
Chaque ligne a un start/end estimé dérivé du squelette viral de F02.
Le timing est continu (pas de gap, pas de chevauchement).
Les visuels se calent automatiquement via la convention MM_SS_mmm.png.

### Coût : 0.00 EUR (Axiome I respecté — l'IRON est Claude dans le sandbox)

*Fer au-dedans, Fer au-dehors.*
