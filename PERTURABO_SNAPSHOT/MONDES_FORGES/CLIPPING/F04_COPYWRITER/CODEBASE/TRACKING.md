# F04_COPYWRITER — TRACKING.md

> *"Le titre est 90% du travail. Le reste suit. Une forteresse tombe par ses mots, pas par sa pierre."*
> *Frégate lourde. Frégate singulière. Elle ne suit pas le pattern 3-phases — elle parle direct au modèle premium, et l'IRON ordonnance seulement.*

---

## RÔLE

F04_COPYWRITER est la **frégate lourde** de la Porte 3. Elle forge le **text_payload** complet pour chaque angle :
- **3 titres calibrés** (pas 1, pas 5) — chacun scoré sur `platform_fit`, `market_fit`, `hook_type`
- **Un paragraphe reframing** (2 lignes max) — la transformation de sens optionnelle
- **Caption** (sous-titre d'ouverture / description courte)
- **Hashtags** — 3 strates (large + moyen + niche)
- **On-screen text** (phrase affichée à une keyframe précise dans le clip)
- **CTA text** — jamais "abonne-toi", toujours subtil ("commente X", "suis pour la suite")

La frégate produit **deux outputs** par angle :
1. `text_payload.json` — format strict, consommé par l'Oracle LACRIMAE
2. `text_payload.md` — format lisible opérateur, prêt à copier-coller au moment de poster

---

## SINGULARITÉ — RUPTURE DU PATTERN 3-PHASES

Contrairement aux autres frégates qui dialoguent avec l'IRON (Claude sandbox) en 3 phases (prepare → IRON → finalize), F04 **contourne** ce pattern :

```
Phase A : setup_context       (l'IRON sandbox rassemble l'ARCHIVUM pertinent)
Phase B : premium_generation  (la frégate parle DIRECT au modèle premium
                                via clé API dédiée — aucun IRON 
                                intermédiaire pour la génération)
Phase C : iron_ordonnancing    (l'IRON sandbox récupère la sortie premium,
                                valide cohérence, classe, tag, vérrouille)
Phase D : finalize + ledger    (IW_CUSTOS enregistre — cohérence frégates)
```

**Justification** : le texte porte 90% du lift viral (Ogilvy : "The reader isn't going to read your body copy unless your headline wins"). Le sandbox bridé ne suffit pas. Le modèle premium génère, l'IRON sandbox ordonnance et enregistre dans le ledger pour garder la cohérence du système.

---

## INPUTS

| Input | Source | Format | Obligatoire |
|---|---|---|---|
| `angles.json` | ANGLESMITH | JSON | ✅ |
| `campaign_verdict.json` | F02_TYRANT_CAMP | JSON | ✅ |
| `source_specimen_<angle>.json` | F03_SOURCE_HUNTER (un par angle) | JSON | ✅ (N specimens) |
| `platform_target` | Warsmith | string | ✅ |
| `market_target` | Warsmith | string | ✅ |
| Clé API premium | `CONTRACTS/copywriter_secrets.json` (gitignored) — nom env var `CLIPPING_PREMIUM_API_KEY` | env | ✅ |

ARCHIVUM injecté dans le prompt (Phase A) :
- `ARCHIVUM/copywriting/hooks_library.md`
- `ARCHIVUM/copywriting/title_formulas.md`
- `ARCHIVUM/copywriting/caption_frameworks.md`
- `ARCHIVUM/copywriting/subliminal_language.md`
- `ARCHIVUM/copywriting/slang_by_market.md`
- `ARCHIVUM/copywriting/hashtags_research.md`
- `ARCHIVUM/copywriting/on_screen_text_patterns.md`
- `ARCHIVUM/copywriting/reference_clips_titles/` (exemples annotés)
- `ARCHIVUM/rules/clipping_rules.md`
- `ARCHIVUM/rules/whop_rules.md`
- `ARCHIVUM/rules/platform_{plateforme}.md`
- `ARCHIVUM/platform_generator/{plateforme}_profile.md`
- `ARCHIVUM/market_generator/{marché}.md`
- `ARCHIVUM/angles/angle_patterns.json`
- `ARCHIVUM/angles/angle_performance.json` (poids nul si < 50 packs)
- `ARCHIVUM/demons/<demon_id>.json` (exemples de titres qui ont marché)
- `ARCHIVUM/knowledge_base/` (sites, docs, transcripts — tout ce qui marche en clipping)
- `ARCHIVUM/learnings/learnings.json` (perf passée)
- `CONTRACTS/copywriting_doctrine.md` — socle doctrinal
- `CONTRACTS/copywriter_systemprompt.md` — system prompt figé (généré par premium à l'init)
- `CONTRACTS/anti_bullshit.md` (liens core)

---

## OUTPUTS

### `OUT/text_payload_<angle_id>.json` (1 par angle)

```json
{
  "campaign_id": "...",
  "angle_id": "...",
  "angle_family": "...",
  "emotion_mode": "...",
  "platform_target": "youtube|tiktok|instagram",
  "market_target": "...",
  
  "titles": [
    {
      "rank": 1,
      "text": "...",
      "platform_fit": <0-10>,
      "market_fit": <0-10>,
      "hook_type": "stat_choc|question|declaration|mystery|contradiction|cible_naming",
      "rationale": "Pourquoi ce titre"
    },
    { "rank": 2, ... },
    { "rank": 3, ... }
  ],
  
  "paragraph": {
    "text": "...",                  // 2 lignes max
    "recommendation": "use|skip",    // F04_COPYWRITER propose
    "override_omniswatch": null,     // Oracle LACRIMAE peut override
    "final_operator": null          // Warsmith a le dernier mot au moment de poster
    // 3 niveaux de veto, dans cet ordre
  },
  
  "caption": "...",
  "hashtags": ["#...", "#...", "#..."],
  "on_screen_text": "..." | null,
  "cta_text": "...",
  
  "compliance": {
    "disclosure": "#ad",
    "ftc_required": true
  },
  
  "check_in_iw_custos": "<ISO8601>"
}
```

### `OUT/text_payload_<angle_id>.md` (1 par angle — lisible opérateur)

```
═══ ANGLE X/N ═══
ANGLE : <angle_family>
ÉMOTION : <emotion_mode>
ENGAGEMENT : <engagement_type>
PLATEFORME : <platform_target>
MARCHÉ : <market_target>

── TITRES (3 calibrés) ──
1. <titre 1>
   [platform_fit: X/10, market_fit: Y/10, hook: Z]
2. <titre 2>
   [...]
3. <titre 3>
   [...]

── PARAGRAPHE (optionnel, 2 lignes) ──
<texte du paragraphe>
 reco: <use|skip>  |  oracle: <null|skip>  |  operateur: <null|use|skip>

── CAPTION ──
<caption>

── HASHTAGS ──
#... #... #ad

── ON-SCREEN TEXT (keyframe optionnelle) ──
<texte>

── CTA ──
<cta_text>
```

Ce `.md` est ce que le Warsmith lise au moment de poster. Pas le JSON.

---

## SYSTEM PROMPT — INIT À NE PAS REFAIRE

Le `CONTRACTS/copywriter_systemprompt.md` est **généré par le modèle premium lui-même** à la première initialisation de la frégate. Procédure (one-time) :

1. Le Warsmith alimente le prompt d'init avec :
   - La doctrine copywriting (10 sections, à remplir par le Warsmith — voir `CONTRACTS/copywriting_doctrine.md`)
   - Un exemple de bon text_payload JSON cible
   - La liste des 8 sous-dossiers de `ARCHIVUM/copywriting/`
2. Le modèle premium produit le system prompt final, qui sera figé dans `copywriter_systemprompt.md`.
3. Pour toutes les exécutions suivantes (Phase B), ce system prompt est utilisé tel quel.

**Ne pas régénérer le system prompt à chaque campagne — il est figé après l'init.**

---

## CLÉ API PRÉMIUM

La clé API de F04_COPYWRITER est la **plus puissante** que le Warsmith possède. Elle est stockée dans :
- `CONTRACTS/copywriter_secrets.json` — fichier **gitignored**, ne contient que la référence à la variable d'env, jamais la clé en clair
- Variable d'env : `CLIPPING_PREMIUM_API_KEY` (sur la machine du Warsmith)

Le fichier public (commité) est `CONTRACTS/copywriter_secrets.example.json` qui documente la structure attendue sans exposer aucune clé.

---

## PATTERN D'EXÉCUTION — 4 PHASES

### Phase A — setup_context

```
python copywriter.py --setup-context --angle <angle_id> --platform <p> --market <m>
```

L'IRON (sandbox Claude) rassemble :
- Le contenu de `ARCHIVUM/copywriting/*` (les 8 sous-dossiers)
- `ARCHIVUM/rules/*`
- `ARCHIVUM/platform_generator/{p}_profile.md`
- `ARCHIVUM/market_generator/{m}.md`
- `ARCHIVUM/angles/angle_patterns.json` + `angle_performance.json`
- `ARCHIVUM/demons/*` (exemples de titres gagnants)
- `ARCHIVUM/knowledge_base/*` (sites, docs, transcripts)
- `ARCHIVUM/learnings/learnings.json`
- `CONTRACTS/copywriting_doctrine.md`
- `CONTRACTS/copywriter_systemprompt.md`
- `CONTRACTS/anti_bullshit.md` (liens core)
- L'angle actif (depuis ANGLESMITH)
- Le specimen source (depuis F03_SOURCE_HUNTER)

→ Output : `IN/copywriter_context_<angle_id>.json` (contexte strukturé pour le premium)

### Phase B — premium_generation

```
python copywriter.py --generate --angle <angle_id>
# Lit CLIPPING_PREMIUM_API_KEY depuis l'env
# Dialog DIRECT avec le modèle premium (pas d'IRON intermédiaire)
```

La frégate parle directement au modèle premium (via son SDK dédié). Le system prompt est `copywriter_systemprompt.md`. Le user prompt est le contexte Phase A + la mission "forge 3 titres + paragraphe + caption + hashtags + on-screen pour cet angle".

→ Output : `OUT/text_payload_raw_<angle_id>.json` (sortie brute du premium)

### Phase C — iron_ordonnancing

```
python copywriter.py --ordonnance --angle <angle_id>
# L'IRON (sandbox Claude) récupère le raw premium
```

L'IRON :
- Valide la cohérence (pas de contradiction, pas d'hallucination de hook_type)
- Classe les 3 titres par `rank` (1, 2, 3) selon `platform_fit + market_fit + hook_strength`
- Tag le `paragraph.recommendation` ("use" ou "skip" selon pertinence vs angle)
- Vérifie FTC compliance (disclosure "#ad" présent dans caption)
- Vérifie anti-bullshit (pas de "abonne-toi", pas de clickbait pur)

→ Output : `OUT/text_payload_<angle_id>.json` (ordonnancé)

### Phase D — finalize + ledger

```
python copywriter.py --finalize --angle <angle_id>
```

- Check-in `IW_CUSTOS.py` (statut F04 = done pour cet angle)
- Copie le `.json` + génère le `.md` lisible opérateur
- Met à jour `liber_clipping.json`

Pour N angles → répéter Phase A → B → C → D pour chaque. Peut se batcher en // (Phase A en série, B en //, etc.).

---

## CONTRATS RÉFÉRENCÉS

Voir la liste exhaustive ci-dessus dans "ARCHIVUM injecté dans le prompt". La frégate lit TOUT l'ARCHIVUM pertinent pour le copywriting clipping — c'est sa singularité. Elle ne invente pas depuis zéro ; elle synthétise depuis tout ce que PERTURABO sait.

---

## DÉPENDANCES

- **Amont** :
  - F02_TYRANT_CAMP (verdict, squelette référence)
  - F03_SOURCE_HUNTER (source specimen + segments)
  - ANGLESMITH (angle actif)
  - ARCHIVUM complet (la matière à synthétiser)
- **Downstream** :
  - F05_PACKAGER (intègre `text_payload.json` dans `production_pack.json`)
  - Oracle LACRIMAE (lit `text_payload.json` → peut `override_omniswatch` du paragraphe)
  - Warsmith (lit `text_payload.md` au moment de poster → `final_operator`)

---

## 3 NIVEAUX DE VETO DU PARAGRAPHE

Le `paragraph` a une chaîne de décision stricte :

1. **`recommendation`** (F04_COPYWIRITER) — en Phase C, l'IRON tag le paragraphe `"use"` ou `"skip"`. Une reco "skip" ne signifie pas suppression — signifie "à utiliser uniquement à des fins de révision possible".
2. **`override_omniswatch`** (Oracle LACRIMAE, plus tard dans la prod) — initialement `null`. Si l'Oracle estime que le rendu rend le paragraphe redondant ou que le clip n'a pas besoin de paragraphe, il met `"skip"`.
3. **`final_operator`** (Warsmith, au moment de poster) — initialement `null`. Le Warsmith a le dernier mot : `"use"` ou `"skip"` écrase les 2 décisions précédentes.

Règle de résolution : si `final_operator` est non-null, il gagne. Sinon, si `override_omniswatch` est non-null, il gagne. Sinon, `recommendation` s'applique.

---

## HÉRÉSIES

- ❌ "Abonne-toi" / "Like et partage" / "Swipe up" dans CTA / caption / on-screen
- ❌ Clickbait sans payoff : le titre doit livrer dans la vidéo, pas seulement teaser
- ❌ Anti-re кондition : transformer une interview calme en "BEEF EXPLOSIF" = mensonge sur le contenu source (cf. `CONTRACTS/anti_bullshit.md`)
- ❌ Paragraphe > 2 lignes (la longueur-courte-longue est morte)
- ❌ Hashtags sans strate niche (les hashtags "large + moyen" ne suffisent pas — faut la strate niche spécifique)
- ❌ Réutiliser le system prompt sans initialisation一定 (le system prompt est figé après init, mais doit être initialisé une fois)
- ❌ Passer par l'IRON pour la génération (Phase B = premium direct, l'IRON intervient seulement en Phase C pour ordonnancer)

---

## STATUT

| Phase | État | Notes |
|---|---|---|
| Arborescence créée | ✅ | |
| TRACKING.md rédigé | ✅ | Ce fichier |
| Code Python implémenté | ✅ | v1 — commit bdd7012 (tests mock TEST_F04) |
| `copywriter.py` | ✅ | Orchestrator 4 phases + `--init-systemprompt` (one-time) + `--dry-run` |
| `libs/context_builder.py` | ✅ | Phase A — assemble l'ARCHIVUM dans l'IN/context.json (troncature 30k chars/fichier) |
| `libs/premium_client.py` | ✅ | Phase B — client modèle premium direct (OpenAI-compatible urllib + Anthropic, clé via env var, jamais en clair) |
| `libs/iron_ordonnancer.py` | ✅ | Phase C — prompt IRON + mode `--auto-ord` local (classement + reco + auto-fix #ad) |
| `libs/md_renderer.py` | ✅ | Phase D — génère le `.md` lisible opérateur depuis le `.json` |
| `libs/compliance_checker.py` | ✅ | FTC + anti-bullshit + paragraphe 2 lignes + structure minimale |
| `requirements_c04.txt` | ✅ | stdlib pure (client urllib — SDK optionnels documentés) |
| `CONTRACTS/copywriting_doctrine.md` | squelette ✅, contenu ❌ | À remplir par le Warsmith (10 sections — surtout VI subliminal) |
| `CONTRACTS/copywriter_systemprompt.md` | placeholder ✅, contenu ❌ | À générer par premium à l'init : `python copywriter.py --init-systemprompt` (one-time, figé ensuite) |

### Décisions v1 (résumé)
- Check-in IW_CUSTOS F04 seulement quand TOUS les angles ont leur `text_payload_<angle>.json` ordonnancé (évite une transition prématurée de fleet_status).
- Les fichiers > 30k chars de l'ARCHIVUM sont tronqués avec marqueur `[... TRONQUÉ ...]` — la frégate synthétise, elle ne régurgite pas.
- `--generate` refusé tant que le system prompt est le placeholder (sauf `--force`) ; `--dry-run` écrit `IN/premium_call_<angle>.json` sans appel réseau.
- `load_json` en utf-8-sig (robustesse BOM Windows PowerShell).

*Fer au-dedans, Fer au-dehors. Le titre ouvre la brèche, le paragraphe la tient, le loop verrouille la victoire.*

## Addendum MEME — contrat opérationnel validé

Pour le mode MEME, F04 produit par angle un payload brut de revue `text_payload_raw_Axx.json` contenant au minimum le tweet, `text_emotion`, l’émotion et les métadonnées. Le tweet est un mini-récit autonome de trois lignes maximum ; il ne doit pas utiliser de marqueurs `A:` / `B:`.

`text_emotion` est limité à quatre mots et doit identifier la réaction des personnes réellement présentes dans le tweet, par exemple `My sister and me right now:` ou `The two neighbors right now:`. Il ne peut pas conserver une formule, un personnage ou un sujet résiduel d’un autre siège.

Le contexte narratif doit varier angle par angle : relation, lieu, déclencheur et chute sont contrôlés pour empêcher le cannibalisme de forme. Le Champion valide le tweet, le texte motion et les métadonnées ; Oracle peut signaler une anomalie, mais ne valide jamais la Gate à sa place. Les sorties brutes restent en revue jusqu’à cette validation.


## Addendum MEME V2 — source, réaction et motion

F04 reçoit une source sociale déjà archivée par F01. Il ne réécrit jamais `source_post` comme s’il s’agissait de son propre contenu. Pour chaque angle, il produit séparément :

| Champ | Contrat |
|---|---|
| `reaction_angle` | Lecture stratégique explicitement ciblée sur `market_target` |
| `reaction_tweet` | Réaction originale, puissante, autonome et transformatrice ; la paraphrase seule est interdite |
| `text_emotion` | Motion court, simple et cohérent avec les personnes ou l’audience du contexte |
| `metadata` | Titre, description et tags dérivés de la source et de la réaction, sans résidu d’un autre siège |

Le `reaction_tweet` est la pièce stratégique principale. Dix variantes lexicales du même gag sont une cannibalisation. Les angles doivent changer réellement de tension, de lecture, de public visé ou de ressort comique. `text_emotion` ne doit jamais contenir de marqueur `A:` / `B:`, de personnage absent ou de formule héritée d’une autre campagne. Le premium génère si activé ; Oracle contrôle ; seul le Champion valide la Gate F04.

En MEME V2, `source_post.text` reste un input interne de compréhension archivé par F01. La capture PNG de `source_post`, qui contient déjà le tweet et son image, est l’asset visuel destiné au pack final et à LACRIMAE. F04 doit transmettre séparément `reaction_tweet`, `text_emotion` et `metadata` ; il ne doit pas transformer la copie source en faux contenu PERTURABO. Le pack final associe ensuite la capture au `clip_id`, au `meme_tag` et au `channel_id` fournis par l’Opérateur.
