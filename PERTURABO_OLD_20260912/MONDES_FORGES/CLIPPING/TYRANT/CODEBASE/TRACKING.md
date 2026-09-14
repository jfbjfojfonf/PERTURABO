# TYRANT — TRACKING.md (Monde Forge CLIPPING)

> *"L'Oracle voit les Démon avant que les Warsmith ne les pointent du doigt. L'Oracle voit les océans bleus avant que les mers ne vident."*
> *Frégate-Oracle, mode prospectif. Veille Démon dominants hors campagne, cartographie les océans bleus.Common nourrit ARCHIVUM/demons/.*

---

## RÔLE (MODE PROSPECTIF UNIQUEMENT ICI)

`TYRANT/` (à la racine de MONDES_FORGES/CLIPPING/) est la **frégate-Oracle en mode prospectif**. À l'inverse de F02_TYRANT_CAMP (qui analyse une campagne fournie = mode réactif), TYRANT prospectif scanne le **wild clipping** (hors campagne) pour identifier des **Démon dominants** et cartographier leurs **océans bleus unlocked**.

Le Warsmith déclenche TYRANT prospectif sur commande, hors campagne active. La sortie nourrit `ARCHIVUM/demons/` que F02_TYRANT_CAMP lira ensuite pour proposer des océans bleus sur les campagnes futures.

---

## INPUTS

| Input | Source | Format | Obligatoire |
|---|---|---|---|
| Liste de comptes/chaînes à scanner | Warsmith (saisie libre — chaînes clipping virales récentes) | Liste URLs | ✅ |
| Critères de seuil | Defaults dans `TYRANT/IN/tyrant_config.json` (outlier_score > 3x, niche bending) | JSON | ✅ |

---

## OUTPUTS

### `OUT/tyrant_eclaircissement.json`

```json
{
  "scan_id": "...",
  "scanned_at": "<ISO8601>",
  "demons_identified": [
    {
      "demon_id": "<slug>",
      "demon_url": "...",
      "platform": "youtube|tiktok|instagram",
      "views": N,
      "dominant_emotion": "drame|joie|outrage|inspiration|...",
      "dominant_engagement_type": "question|assertion|cliffhanger|...",
      "exploited_territories": ["drame"],         // ce que le Démon couvre
      "blue_ocean_unlocked": [                    // territoires adjacents non saturés
        {
          "territory": "grossophobie",
          "rationale": "...",
          "estimated_saturation": "low|medium|high",
          "blue_ocean_depth": 1                   // toujours 1 — pas 2+
        }
      ],
      "skeleton_extract": {                       // squelette viral du Démon
        "hook_type": "...",
        "loop_technique": "...",
        "structure_narrative": "..."
      }
    }
  ],
  "check_in_iw_custos": "<ISO8601>"
}
```

### Canonical copies
- `ARCHIVUM/demons/<demon_id>.json` — un fichier par Démon, qui sera lu par F02_TYRANT_CAMP plus tard

---

## MÉTHODE — OCÉAN BLEU 1 COUCHE

Le Démon a une émotion dominante (ex : `drame`). TYRANT prospectif propose des re-ciblages non saturés sur la même forme narrative — mais **1 couche de profondeur seulement**.

Exemple validé :
```
Démon → drame
  └→ blue_ocean_unlocked[0] = grossophobie  (depth=1)
  └→ blue_ocean_unlocked[1] = gens toxiques (depth=1)
  
INTERDIT :
  grossophobie → violence verbale (depth=2) = hérésie
```

Si F02_TYRANT_CAMP tente d'empiler 2 couches, elle doit rejeter.

---

## PATTERN D'EXÉCUTION

```
Phase 1 : prepare
   python tyrant.py --prepare --scan-list IN/scan_list.json
   → génère IN/tyrant_prompt.json

Phase 2 : IRON (Claude sandbox)
   Le Warsmith copie-colle le prompt.
   L'IRON scanne les clips (via yt-dlp metrics + transcripts locaux si disponibles),
   identifie les Démon (outlier_score > 3x), cartographie les émotions dominantes,
   propose les océans bleus 1 couche.
   → Écrit OUT/tyrant_eclaircissement.json

Phase 3 : finalize
   python tyrant.py --finalize
   → Copie chaque démon vers ARCHIVUM/demons/<demon_id>.json
   → Check-in IW_CUSTOS.py
```

---

## CONTRATS RÉFÉRENCÉS

- `ARCHIVUM/rules/clipping_rules.md`
- `HERESIE/CONTRACTS/tyrant_prompt.md` (liens core) — modèle de prompt Oracle
- `HERESIE/CONTRACTS/anti_bullshit.md` (liens core)
- `ARCHIVUM/knowledge_base/transcripts/` — pour lire les transcripts des Démon déjà scrapés

---

## DÉPENDANCES

- **Amont** : Warsmith (scan_list)
- **Downstream** : `ARCHIVUM/demons/` (nourri) → F02_TYRANT_CAMP (lit)
- **Auxiliaire** : peut utiliser `F00_CAPTEURS/` pour scrap les métriques des Démon

---

## HÉRÉSIES

- ❌ Re-ciblage au-delà de 1 couche
- ❌ Identifier des Démon sans preuve (outlier_score quantitatif obligatoire)
- ❌ Suggérer des sources alternatives à la future campagne (TYRANT prospectif ne voit que le wild, pas les assets d'une campagne spécifique)

---

## STATUT

| Phase | État | Notes |
|---|---|---|
| Arborescence créée | ✅ | |
| TRACKING.md rédigé | ✅ | Ce fichier |
| Code Python implémenté | ✅ (v1) | |
| `tyrant.py` | ✅ (v1) | Wrapper 3 phases (--prepare / --auto / --finalize) |
| `libs/outlier_scorer.py` | ✅ (v1) | Calcul outlier_score > 3x (views / baseline) |
| `libs/emotion_classifier.py` | ✅ (v1) | Classification émotion dominante (keywords titre/transcript) |
| `libs/blue_ocean_mapper.py` | ✅ (v1) | Mapper territoires adjacents 1 couche + clamp profondeur |
| `libs/demon_archivist.py` | ✅ (v1) | Écrit demon_id.json dans ARCHIVUM/demons/ |
| `requirements_tyrant.txt` | ✅ | yt-dlp + youtube-transcript-api (Warsmith/IRON Phase 2) |

Référence d'implémentation : `HERESIE/TYRANT/CODEBASE/tyrant.py` dans le core (squelette structurel probablement réutilisable, mais adapter au prospectif clipping).

*Fer au-dedans, Fer au-dehors.*
