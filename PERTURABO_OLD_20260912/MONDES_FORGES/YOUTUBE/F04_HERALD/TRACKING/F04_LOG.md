# F04_LOG — Frégate HERALD

> *Étanchéité absolue. Cette frégate ne communique que via liber_perturabo.json.*
> *Le fer qui porte l'étendard.*

---

## [INIT] F04_HERALD déployée — Codebase complet

Frégate de génération de miniature de la IV Légion. Analyse la thumbnail virale
d'origine (Visual Skeleton), génère une nouvelle image adaptée à la niche,
et produit un prompt Gemini de backup + les instructions texte Canva.

### Codebase déployé
- `herald.py` — Orchestrateur 3 phases (prepare → IRON → finalize)
- `thumb_downloader.py` — Télécharge la thumbnail depuis l'URL (requests)
- `contracts_loader.py` — Charge iron_prompt + anti_bullshit + thumbnail_checklist + ARCHIVUM
- `requirements_f04.txt` — requests (pour télécharger l'image)

### Architecture hybride
Phase 1 (--prepare) : herald.py télécharge la thumbnail + assemble le prompt (image base64)
Phase 2 (IRON)      : Claude (sandbox) analyse l'image (Vision), génère la nouvelle image
                      (image_generator), rédige le prompt Gemini backup + instructions Canva
Phase 3 (--finalize): herald.py valide thumbnail_concept.json → check-in IW_CUSTOS

### Génération d'image directe
L'IRON utilise image_generator (dans le sandbox) pour générer thumbnail.png directement.
Pas de Midjourney. Pas d'outil externe. Pas de copier-coller manuel.
Backup : prompt Gemini 3.1 Pro fourni si la qualité de l'image générée est insuffisante.

### Outputs
- `thumbnail_concept.json` — visual skeleton + image générée + prompt Gemini + instructions Canva
- `thumbnail.png` — l'image générée par l'IRON (image_generator)

### Flux interne
1. Télécharge la thumbnail d'origine (de specimen.json → URL maxresdefault)
2. Charge les contrats (iron_prompt, anti_bullshit, thumbnail_checklist)
3. Charge l'ARCHIVUM (rules/ — règles de psychologie visuelle)
4. Encode l'image en base64 + assemble le prompt
5. L'IRON (Claude) analyse le Visual Skeleton (composition, couleurs, émotion, texte, curiosity gap)
6. L'IRON génère la nouvelle image (image_generator) → thumbnail.png
7. L'IRON rédige le prompt Gemini de backup
8. L'IRON rédige les instructions texte Canva (3-4 mots, police, couleur, position)
9. L'IRON écrit thumbnail_concept.json
10. herald.py valide → check-in IW_CUSTOS.py

### Coût : 0.00 EUR (Axiome I respecté — l'IRON est Claude dans le sandbox, image_generator est gratuit)

*Fer au-dedans, Fer au-dehors.*
