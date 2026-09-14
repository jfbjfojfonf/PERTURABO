# MANIFEST.md — Manifeste de livraison du Monde Forge CLIPPING

> *Liste exhaustive des fichiers créés. L'implémenteur Python lira ce manifest + chaque TRACKING.md pour savoir exactement quoi coder.*

---

## Scope de la livraison

- ✅ **Arborescence complète** : 82 dossiers créés
- ✅ **README.md racine** : vue d'ensemble du forge (positionnement, inputs, portes, frégates, ARCHIVUM, hérésies)
- ✅ **TRACKING.md par frégate** : doc dédiée à chaque frégate (rôle, inputs, outputs, pattern d'exécution, contrats, dépendances, hérésies, statut)
- ✅ **CONTRACTS** : copywriting_doctrine.md, copywriter_systemprompt.md (placeholder), copywriter_secrets.example.json, whop_rules.md, clipping_rules.md, production_pack_schema.json, clipping_sites_to_scrap.example.json
- ✅ **ARCHIVUM** : 10 zones + README pour chaque zone importante + squelettes JSON initiaux (learnings, angle_patterns, angle_performance)
- ✅ **.gitignore** : protège les secrets et le runtime
- ✅ **TRACKING/INDEX.md** : cartographie des journaux

Cette livraison est **la trame stratégique**. Aucun code Python n'est écrit. La production du code est déléguée à un autre model qui suivra religieusement les TRACKING.md.

---

## Inventaire par catégorie

### 📄 Fichiers de pilotage (racine + tracking)

| Fichier | Statut | Rôle |
|---|---|---|
| `README.md` | ✅ finalisé | Vue d'ensemble du forge |
| `TRACKING/CLIPPING_LOG.md` | ✅ finalisé | Journal général (init, portes, statuts) |
| `TRACKING/INDEX.md` | ✅ finalisé | Cartographie des journaux |
| `MANIFEST.md` | ✅ finalisé | Ce fichier |
| `.gitignore` | ✅ finalisé | Secrets + runtime + caches |

### ⚔️ TRACKING.md des 9 composants

| Composant | Fichier TRACKING.md | Statut | Code Python |
|---|---|---|---|
| F01_SCOUT | `F01_SCOUT/CODEBASE/TRACKING.md` | ✅ rédigé | ✅ **implémenté (v1)** — scout.py + libs recon/enrich/scribe |
| F02_TYRANT_CAMP | `F02_TYRANT_CAMP/CODEBASE/TRACKING.md` | ✅ rédigé | ✅ **implémenté (v1)** — tyrant_camp.py + libs skeleton/blue_ocean/fit |
| ANGLESMITH | portée par F02 (README.md) | ✅ rédigé (README mécanisme N angles) | ✅ **implémenté (v1)** — anglesmith.py + libs angle_forger/learnings_weight |
| F03_SOURCE_HUNTER | `F03_SOURCE_HUNTER/CODEBASE/TRACKING.md` | ✅ rédigé | ✅ **implémenté (v1)** - source_hunter.py + libs transcript_loader/segment_matcher/duration_guard |
| F04_COPYWRITER | `F04_COPYWRITER/CODEBASE/TRACKING.md` | ✅ rédigé (le plus détaillé — frégate lourde 4 phases) | ✅ **implémenté (v1)** — copywriter.py 4 phases premium direct + libs context_builder/premium_client/iron_ordonnancer/compliance_checker/md_renderer |
| F05_PACKAGER | `F05_PACKAGER/CODEBASE/TRACKING.md` | ✅ rédigé | ✅ **implémenté (v1)** — packager.py assemble/finalize + libs schema_validator/reference_style_extractor |
| F06_TRACKER | `F06_TRACKER/CODEBASE/TRACKING.md` | ✅ rédigé | ✅ **implémenté (v1)** — tracker.py post/submit/views/payout/close + libs readings_validator/learnings_aggregator/channel_performance_updater (+ IW_CUSTOS close-campaign) |
| TYRANT (prospectif) | `TYRANT/CODEBASE/TRACKING.md` | ✅ rédigé | ✅ **implémenté (v1)** — tyrant.py + libs outlier/emotion/blue_ocean/archivist |
| F00_CAPTEURS | `F00_CAPTEURS/CODEBASE/TRACKING.md` | ✅ rédigé | ✅ **implémenté (v1)** — capteurs.py scan/scan-demons commandités Warsmith + libs whop_scanner/clipping_ecosystem_scanner/campaign_context_scanner/demon_scanner |
| ORCHESTRATOR | `ORCHESTRATOR/CODEBASE/TRACKING.md` | ✅ rédigé | ✅ **implémenté (v1)** — orchestrator.py + gates.py + 4 libs |

### 🧱 Fichiers runtime du nerf central (vague 1 implémentée)

| Fichier | Statut | Rôle |
|---|---|---|
| `IW_CUSTOS.py` (racine forge) | ✅ implémenté | Gardien du ledger — check-out/check-in/validate/status |
| `liber_clipping.json` (racine forge) | ✅ prêt | État inter-frégates (singulier, 1 siège max) |
| `ORCHESTRATOR/CODEBASE/orchestrator.py` | ✅ implémenté | CLI start-siege/gate/resume/status/close-siege |
| `ORCHESTRATOR/CODEBASE/gates.py` | ✅ implémenté | Les 4 Portes CLIPPING |
| `ORCHESTRATOR/CODEBASE/libs/` (4 libs) | ✅ implémenté | ledger_manager, siege_initializer, gate_validator, omnis_watch_distributor |

### 📜 CONTRACTS/

| Fichier | Statut | Rempli par |
|---|---|---|
| `copywriting_doctrine.md` | squelette (10 sections structurées) | Le Warsmith doit remplir chaque section — surtout VI (subliminal, savoir secret) |
| `copywriter_systemprompt.md` | placeholder | Génération par premium à l'init (one-time) |
| `copywriter_secrets.example.json` | ✅ schéma public | Le Warsmith crée `copywriter_secrets.json` (gitignored) avec clé + model_id |
| `whop_rules.md` | squelette (sections documentées) | Warsmith confirme chiffres + cas particuliers |
| `clipping_rules.md` | ✅ 8 règles documentées (C1-C7) | Warsmith peut enrichir cas particuliers |
| `production_pack_schema.json` | ✅ schéma canonique | Contrat figé PERTURABO ↔ OMNIS_WATCH |
| `clipping_sites_to_scrap.example.json` | ✅ schéma public | Warsmith crée le .json réel avec les sites qu'il veut scraper |

### 📚 ARCHIVUM/

| Zone | README | Squelettes JSON | Statut |
|---|---|---|---|
| `rules/` | ✅ | n/a (squelettes dans `CONTRACTS/`) | squelettes — Warsmith à remplir pour platform_tiktok/shorts/reels_md |
| `campaign/` | ✅ | n/a | runtime (Warsmith y dépose directive.md avant chaque siège) |
| `platform_generator/` | ✅ | n/a | squelettes — Warsmith remplit youtube/tiktok/instagram_profile.md |
| `market_generator/` | ✅ | n/a | squelettes — Warsmith remplit us_young_english.md |
| `knowledge_base/` | ✅ | n/a | squelettes — Warsmith peuple sites/, docs/, transcripts/ |
| `copywriting/` | ✅ | n/a | squelettes — 8 sous-dossiers, savoir secret Warsmith |
| `angles/` | ✅ | ✅ `angle_patterns.json` + `angle_performance.json` | squelettes — Warsmith catalogue les patterns |
| `demons/` | ✅ | n/a | runtime (TYRANT prospectif y écrit) |
| `channels/` | ✅ | n/a | runtime (Warsmith y crée un sous-dossier par compte) |
| `learnings/` | ✅ | ✅ `learnings.json` (squelette initial) | runtime (F06 nourrit) |
| `ledgers/` | n/a (core tient IW_CUSTOS.py à racine) | n/a | runtime |
| `templates/` | n/a | n/a | réservé — usage futur |

### 🧱 Sous-dossiers CODEBASE/ (vides — contenu `.gitkeep`)

Chaque frégate a :
- `CODEBASE/` — destiné à recevoir le code Python (à implémenter par autre model)
- `CODEBASE/libs/` — bibliothèques auxiliaires (à implémenter)
- `IN/` — inputs runtime
- `OUT/` — artefacts produits runtime
- `TRACKING/` — extendable si besoin (par défaut seulement `.gitkeep`)

`SHARED/` dispose de `IN/` + `OUT/` pour les ressources communes.

`ORCHESTRATOR/CODEBASE/TRACKING.md` documente aussi la gestion de `IW_CUSTOS.py` à la racine du forge (à copier du core — script registre).

---

## ⚠️ Note sécurité

Un token GitHub a été partagé en clair dans le chat pendant la session (token redacted par sécurité). Il a été utilisé **temporairement** pour cloner PERTURABO et pousser le forge.

**Le Warsmith doit** :
1. Révoquer ce token immédiatement sur https://github.com/settings/tokens (il est publiquement compromis)
2. Ne jamais le réutiliser
3. Ne plus partager de token en clair dans le chat
4. Créer un nouveau token pour les sessions futures, à stocker dans une var d'env locale

---

## 🎯 Prochaines étapes pour le Warsmith

### Phase 1 — Remplir la doctrine et l'ARCHIVUM (savoir secret)

1. Remplir `CONTRACTS/copywriting_doctrine.md` (sections I à X) — surtout VI (subliminal, savoir secret)
2. Remplir `ARCHIVUM/copywriting/` (8 sous-dossiers) — c'est le musée du copywriting:
   - `hooks_library/` — types de hooks + exemples
   - `title_formulas/` — formules de titres
   - `caption_frameworks/` — structures caption
   - `subliminal_language/` — le savoir secret
   - `slang_by_market/` — codex slang US jeune + bannis TikTok
   - `hashtags_research/` — stratégies 3-strates + bannis
   - `on_screen_text_patterns/` — patterns de keyframe
   - `reference_clips_titles/` — titres gagnants indexés
3. Remplir les platform_generator (youtube/tiktok/instagram)
4. Remplir market_generator (us_young_english par défaut)
5. Peupler knowledge_base/ (sites, docs, transcripts clipping)
6. Pré-peupler `ARCHIVUM/angles/angle_patterns.json` avec les patterns initiaux
7. Créer des sous-dossiers pour ses comptes de clipping dans `ARCHIVUM/channels/`

### Phase 2 — Configurer les secrets

8. À la racine du forge, créer `CONTRACTS/copywriter_secrets.json` (gitignored) :
   ```json
   {
     "env_var_name": "CLIPPING_PREMIUM_API_KEY",
     "model_id": "<vrai model premium>",
     "provider": "...",
     "base_url": "...",
     "max_tokens_per_call": 4096,
     "temperature_default": 0.7
   }
   ```
9. Sur sa machine : `export CLIPPING_PREMIUM_API_KEY=...` (jamais committé)

### Phase 3 — Initialiser le system prompt (one-time)

10. Une fois le copywriting doctrine rempli + musée copywriting peuplé, exécuter le script d'init (à implémenter) :
    ```
    python copywriter.py --init-systemprompt
    ```
    Le modèle premium lit la doctrine + le musée → génère `CONTRACTS/copywriter_systemprompt.md` (figé ensuite).

### Phase 4 — Déléguer le code Python

11. Lancer un autre model (Claude, GPT, etc.) sur ce dépôt avec comme instruction :
    "Lis tous les TRACKING.md du forge CLIPPING + README.md + MANIFEST.md + CONTRACTS/. Implémente tous les scripts Python des frégates en suivant religieusement chaque TRACKING.md. Le schéma du production pack doit être respecté strictement (CONTRACTS/production_pack_schema.json)."
12. Le model implémente `*.py` according aux TRACKING.md

### Phase 5 — Premier siège

13. First siege :
    - Déposer `directive.md` + `reference_clip.json` dans `ARCHIVUM/campaign/`
    - Préparer `clipping_sites_to_scrap.json` (si tu veux scanner plus large)
    - Lancer `python orchestrator.py --start-siege ...` (à implémenter)
    - Suivre les 4 Portes avec validation Warsmith à chaque.

---

*Fer au-dedans, Fer au-dehors. La structure est en place. La doctrine reste à écrire. Le code suit.*
