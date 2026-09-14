# F06_LOG — Frégate IDENTITY_FORGE

> *Étanchéité absolue. Cette frégate ne communique que via liber_perturabo.json.*
> *Le fer qui forge l'identité.*

---

## [INIT] F06_IDENTITY_FORGE déployée — Codebase complet

Frégate de création d'identité de chaîne YouTube de la IV Légion.
Forge le nom, la description, les tags, le tone of voice, les codes visuels,
le banner et le logo d'une nouvelle chaîne à partir du specimen et du niche report.

### Codebase déployé
- `identity_forge.py` — Orchestrateur 3 phases (prepare → IRON → finalize) + register
- `contracts_loader.py` — Charge system_prompt + iron_prompt + anti_bullshit + ARCHIVUM
- `requirements_f06.txt` — Zéro dépendance (stdlib uniquement)

### Architecture hybride
Phase 1 (--prepare) : identity_forge.py assemble le prompt (niche + specimen + contrats + ARCHIVUM)
Phase 2 (IRON)      : Claude (sandbox) analyse le specimen, dérive le tone of voice automatiquement,
                      propose 10 noms classés du meilleur au pire, génère banner + logo via image_generator,
                      écrit channel_identity.json
Phase 3 (--finalize): identity_forge.py valide channel_identity.json → check-in IW_CUSTOS
Register (--register): Enregistre la chaîne dans ARCHIVUM/channels/ + met à jour registry.json

### Outputs
- `channel_identity.json` — nom (10 classés), description, tags, tone of voice, codes visuels, format standard
- `banner.png` — bannière YouTube générée par l'IRON (image_generator)
- `logo.png` — logo/avatar de chaîne généré par l'IRON (image_generator)
- `iron_prompt.txt` — le prompt assemblé (phase 1)

### Tone of voice — dérivation automatique
L'IRON analyse le specimen (transcription + métadonnées) et dérive automatiquement :
- Registre verbal (dense, factuel, etc.)
- Rythme (métronomique, ~35s par type, etc.)
- Vocabulaire signature
- Personnalité
- Ce que la chaîne ne FAIT JAMAIS

### Noms de chaîne — 10 propositions classées
L'IRON propose 10 noms, classés du MEILLEUR au PIRE.
Pour chaque nom : rationale + score mémorabilité + score SEO + score marque.
Le Warsmith choisit le nom à la validation.

### Banner + Logo — générés via image_generator
L'IRON génère directement :
- banner.png (2560x1440, ratio 16:9, zone safe au centre)
- logo.png (carré 1:1, pictogramme simple, lisible à 32x32)
Pas d'outil externe. Pas de Canva. Pas de Midjourney. Coût : 0.00 EUR.

### CHANNEL_REGISTRY
Après validation du Warsmith (--register), la chaîne est enregistrée dans :
```
ARCHIVUM/channels/
├── registry.json          # Index de toutes les chaînes
├── [channel_slug]/
│   ├── channel_identity.json   # Nom, desc, tags, tone, codes
│   ├── banner.png
│   ├── logo.png
│   ├── videos/
│   │   ├── video_001.json      # Métadonnées du siège #1
│   │   └── ...
│   └── performance.json        # Vues, CTR, rétention (Phase 1 manuel)
```

### Performance tracking
Phase 1 (actuel) : performance.json existe mais reste vide. Le Warsmith remplit manuellement.
Phase 2 (plus tard) : Les CAPTEURS nourrissent performance.json automatiquement via yt-dlp.

### Flux dans le Mode Chaîne (mis à jour)
```
PORTE 1 — TYRANT éclaire le territoire
    ↓
F05_GRAND_COMPASS — niche bending + océan bleu
    ↓
Warsmith valide la niche
    ↓
F06_IDENTITY_FORGE — forge l'identité de la chaîne
    ↓                     (nom, desc, tags, banner, logo, tone, codes)
Warsmith valide l'identité (choisit le nom)
    ↓
F01_SENTINEL → F02_BREACHER → F03_FORGEWARD → F04_HERALD
    ↓                     (le premier siège, dans les codes de la chaîne)
PORTE 4 — Artefact final
    ↓
Chaîne enregistrée dans ARCHIVUM/channels/
```

### Flux dans le Mode Vidéo (chaîne existante)
```
Warsmith : "Nouvelle vidéo sur [chaîne] — sujet : ..."
    ↓
ORCHESTRATOR charge ARCHIVUM/channels/[slug]/channel_identity.json
    ↓
PERTURABO sait : tone, format, palette, style, structure
    ↓
F01_SENTINEL → F02_BREACHER → F03_FORGEWARD → F04_HERALD
    ↓           (tous les outputs respectent les codes de la chaîne)
PORTE 4 — Artefact final
    ↓
Vidéo enregistrée dans ARCHIVUM/channels/[slug]/videos/
```

### Coût : 0.00 EUR (Axiome I respecté — l'IRON est Claude dans le sandbox)

*Fer au-dedans, Fer au-dehors.*
