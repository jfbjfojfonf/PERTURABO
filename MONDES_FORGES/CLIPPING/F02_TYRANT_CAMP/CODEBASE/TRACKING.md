# F02_TYRANT_CAMP — TRACKING.md

> *"L'Oracle voit la forteresse. L'Oracle voit l'océan bleu. L'Oracle ne ment pas — il éclaire."*
> *Frégate-stratège de la Porte 1. Elle ne produit pas des vidéos, elle produit des verdicts.*

---

## RÔLE

F02_TYRANT_CAMP est la **frégate stratège de la Porte 1**. Elle prend en entrée le `source_specimen.json` produit par F01_SCOUT et sort un **verdict GO/NO-GO** accompagné de l'identification d'un **océan bleu** potentiel — sur la MÊME source que le Démon de la campagne (pas d'hérésie : on ne re-cible jamais au-delà de 1 couche).

Elle prose aussi le squelette viral du clip de référence (preuve de ce qui marche).

---

## INPUTS

| Input | Source | Format | Obligatoire |
|---|---|---|---|
| `source_specimen.json` | F01_SCOUT | JSON | ✅ |
| `directive.md` | `ARCHIVUM/campaign/directive.md` | Markdown | ✅ |
| `platform_target` | Warsmith (input 3 du Warsmith) | string | ✅ |
| `market_target` | Warsmith (input 4) | string | ✅ |
| `cartographie_écosystème` | F00_CAPTEURS (si exécuté avant Porte 1) | JSON | Optionnel mais recommandé |

---

## OUTPUTS

### `OUT/campaign_verdict.json`

```json
{
  "campaign_id": "...",
  "verdict": "GO|NO-GO",
  "verdict_justification": "...",
  
  "reference_skeleton": {
    "hook_type": "...",
    "emotion_dominante": "...",
    "structure_narrative": "...",
    "loop_technique": "...",
    "engagement_type": "...",
    "endroits_preuve": ["..."]    // moments du clip ref qui prouvent le squelette
  },
  
  "demon_analysis": {
    "demon_id": "...",
    "dominant_emotion": "drame|joie|outrage|...",
    "exploited_territories": ["drame"],
    "blue_ocean_unlocked": [
      {
        "territory": "grossophobie",
        "rationale": "même source, même forme, mais re-ciblée sur un angle 
                      non saturé observé sur le scraping",
        "estimated_saturation": "low|medium|high",
        "blue_ocean_depth": 1
      },
      {
        "territory": "gens toxiques",
        "rationale": "...",
        "estimated_saturation": "low",
        "blue_ocean_depth": 1
      }
    ]
  },
  
  "direct_analysis": {
    "campaign_fit_platform": <0-10>,
    "campaign_fit_market": <0-10>,
    "campaign_budget_remaining": "...",
    "cpm_expected": "...",
    "saturation_level": "low|medium|high"
  },
  
  "check_in_iw_custos": "<ISO8601>"
}
```

### Autres outputs
- `ARCHIVUM/campaign/verdict.json` (copie canonique)
- `ARCHIVUM/campaign/reference_skeleton.json` (canonical squelette)
- `OUT/scout_report.md` (synthèse lisible pour le Warsmith à la Porte 1)

---

## DEUX MODES (F02 + TYRANT)

F02_TYRANT_CAMP et la frégate `TYRANT/` partagent la capacité "Oracle". F02 est spécialisée sur une campagne (mode réactif). TYRANT/ est le mode prospectif global (veille Démon dominants hors campagne).

| Mode | Qui | Quand | Sortie |
|---|---|---|---|
| Réactif | F02_TYRANT_CAMP | Pour chaque campagne fournie par le Warsmith | `campaign_verdict.json` |
| Prospectif | TYRANT/ | Sur commande Warsmith, hors campagne, pour identifier des Démon dans le wild | `tyrant_eclaircissement.json` qui nourrit `ARCHIVUM/demons/` |

F02 lit `ARCHIVUM/demons/` (synthèse des Démon cartographiés par TYRANT prospectif) pour identifier l'océan bleu de la campagne. **Démon de campagne** et **Démon veille** peuvent être identiques ou différents.

---

## PATTERN D'EXÉCUTION

Pattern **3-phases standard** :

```
Phase 1 : prepare
   python tyrant_camp.py --prepare --specimen ../F01_SCOUT/OUT/source_specimen.json
   → génère IN/tyrant_camp_prompt.json (prompt pour l'IRON)

Phase 2 : IRON (Claude sandbox)
   Le Warsmith copie le prompt dans Claude.
   L'IRON analyse : le squelette de référence, le Démon, les océans bleus,
   le fit plateforme/marché, la saturation.
   → Écrit OUT/campaign_verdict.json

Phase 3 : finalize
   python tyrant_camp.py --finalize
   → Valide cohérence + check-in IW_CUSTOS.py
   → Copie vers ARCHIVUM/campaign/verdict.json
   → Met à jour liber_clipping.json (statut F02 = done, verdict disponible Porte 1)
```

---

## MÉTHODE OCÉAN BLEU

Démon = clip dominant avec une émotion dominante (ex : `drame`).
F02 propose des **re-ciblages** sur des territoires adjacents non saturés, mais **uniquement sur la même source** que celle de la campagne (assets Whop).

Règles strictes :
- Profondeur océan bleu : **1 couche maximum**. Exemple Démon (drame) → grossophobie. On ne re-cible pas une 2e fois (grossophobie → violence verbale en ligne = interdit).
- Le re-ciblage ne change pas la source — il change l'angle d'attaque narratif.
- Critère de saturation : lu depuis `ARCHIVUM/demons/<demon_id>.json` (champ `blue_ocean_unlocked`) — territoire marqué `low` ou `medium` est éligible ; `high` est rejeté.

---

## CONTRATS RÉFÉRENCÉS

- `ARCHIVUM/rules/clipping_rules.md`
- `ARCHIVUM/rules/whop_rules.md`
- `ARCHIVUM/rules/platform_{plateforme}.md`
- `ARCHIVUM/platform_generator/{plateforme}_profile.md`
- `ARCHIVUM/market_generator/{marché}.md`
- `ARCHIVUM/demons/<demon_id>.json` (les Démon veille cartographiés par TYRANT prospectif)
- `CONTRACTS/anti_bullshit.md` (liens core)

---

## DÉPENDANCES

- **Amont** : F01_SCOUT (`source_specimen.json`), F00_CAPTEURS (`cartographie_écosystème` — optionnel mais recommandé), TYRANT prospectif (`ARCHIVUM/demons/`)
- **Downstream** :
  - ANGLESMITH (consomme `verdict.json` pour la Porte 2 — forge les N angles sur `direct_analysis` + `blue_ocean_unlocked`)
  - F04_COPYWRITER (consomme `reference_skeleton` pour calibrer hooks)

---

## HÉRÉSIES

- ❌ Re-ciblage au-delà de 1 couche (profondeur > 1 = hérésie)
- ❌ Suggérer des sources alternatives (assets = forteresse fermée)
- ❌ Verdict sans preuve (chaque assertion du verdict doit être tracée dans le specimen / la cartographie)
- ❌ Ignorer le fit plateforme/marché — chaque verdict doit scorer sur ces axes

---

## STATUT

| Phase | État | Notes |
|---|---|---|
| Arborescence créée | ✅ | |
| TRACKING.md rédigé | ✅ | Ce fichier |
| Code Python implémenté | ✅ (v1) | |
| `tyrant_camp.py` | ✅ (v1) | Wrapper 3 phases (--prepare / --auto / --finalize) |
| `libs/skeleton_extractor.py` | ✅ (v1) | Pré-squelette viral (l'IRON affine) |
| `libs/blue_ocean_finder.py` | ✅ (v1) | Océans bleus depuis ARCHIVUM/demons/ + saturation |
| `libs/fit_scorer.py` | ✅ (v1) | Score fit plateforme × marché × niche (0-10) |
| `requirements_c02.txt` | ✅ | Stdlib pure — rien à installer |
| `anglesmith.py` (ANGLESMITH porté) | ✅ (v1) | Porte 2 — forge des N angles (--prepare/--auto/--finalize) |
| `libs/angle_forger.py` | ✅ (v1) | Combinatoire 4 axes + anti-cannibale (2 axes différenciants min) |
| `libs/learnings_weight.py` | ✅ (v1) | Pondération (poids nul si < 50 packs, activation ensuite) |

Référence d'implémentation : `HERESIE/TYRANT/CODEBASE/tyrant.py` dans le core (squelette structurel probablement réutilisable).

*Fer au-dedans, Fer au-dehors.*
