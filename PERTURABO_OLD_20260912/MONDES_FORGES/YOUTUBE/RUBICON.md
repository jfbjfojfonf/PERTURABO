# LE RUBICON — PLAN DE TRANSFIGURATION

*Charte de passage. Document fondateur. Accès restreint.*

*« Fer au-dedans, Fer au-dehors. »*

---

## I. Le Baptême

Le projet s'appelle **PERTURABO**.

Perturabo, Primarch de la IV Légion — les Iron Warriors. Le Lord of Iron. Le Tyrant of Olympia. Le maître du siège méthodique. Celui dont la capacité d'analyse était si démentielle qu'il pouvait regarder une fortification et en voir chaque faille, chaque faiblesse structurelle, chaque point de rupture — avant que le premier coup ne soit porté.

PERTURABO est l'outil qui **regarde une vidéo YouTube et en voit le squelette caché**. Comme le Primarch regardait une forteresse et en voyait les fractures. L'analyse précède le siège. La compréhension précède la production.

Mais Perturabo ne travaillait pas seul. Sa légion — les Iron Warriors — était organisée en Grand Companies, chaque unité ayant un rôle de siège précis. Reconnaissance, sape, brèche, forge, cartographie. Aucun organe ne faisait le travail d'un autre. La méthode était le siège, et le siège était une discipline, pas un assaut.

Et avant chaque siège, Perturabo déployait ses **Capteurs** — un réseau de surveillance qui ne dormait jamais, qui observait l'ennemi en continu, qui capturait chaque mouvement, chaque pattern, chaque faiblesse. Les Capteurs nourrissaient l'analyse. L'analyse nourrissait le siège. Le siège nourrissait la victoire.

PERTURABO. Le moteur analytique de siège du territoire YouTube.

---

## II. L'Autopsie du Chassis V1

Le chassis actuel (`youtube-mcp/`) est en **veille**. Il fonctionne, mais il est manuel. L'humain est présent à chaque étape. Il lance les commandes une par une. Il n'y a pas de portes — il n'y a que des marches d'escalier que l'humain gravit lui-même.

### Ce qui peut survivre à la greffe

| Composant V1 | Verdict | Raison |
|---|---|---|
| `youtube_fetch.py` (OSINT) | ✅ Survit | Récupération de données autonome, ne nécessite pas de main humaine |
| `web_search.py` (DuckDuckGo) | ✅ Survit | Recherche autonome pour validation océan bleu |
| `skeleton_checklist.json` | ✅ Survit | Contrat structuré, lisible par machine |
| `anti_bullshit.md` | ✅ Survit | Filtre doctrinal, essentiel au Tyrant |
| `system_prompt.md` | ⚠️ Muté | Doit être réécrit pour intégrer la doctrine complète (rôles, portes, ledger, capteurs) |
| `memory/` (structure) | ✅ Survit | La Mémoire Impériale est la fondation — elle ne traverse pas, elle **est** le sol |

### Ce qui doit mourir

| Composant V1 | Verdict | Raison |
|---|---|---|
| CLI manuel (`main.py` argparse) | ❌ Meurt | Le Warsmith ne lance pas des commandes une par une. Il se présente aux portes. |
| Exécution "one-shot" | ❌ Meurt | Pas de mémoire entre les étapes. Si ça plante à l'étape 3, tout recommence. |
| Absence de Ledger | ❌ Meurt | Chaque session repart de zéro. Incompatible avec la doctrine. |
| Absence du Tyrant | ❌ Meurt | L'IA traite mais ne **voit** pas le territoire avant le siège. |
| Absence de Capteurs | ❌ Meurt | Pas de surveillance continue des concurrents. Perturabo ne dort jamais. |
| `video_mode.py` (monolithique) | ❌ Meurt | Une fonction qui fait tout = un organe qui fait tout. Incompatible avec les frégates. |
| `channel_mode.py` (monolithique) | ❌ Meurt | Même raison. Doit être éclaté en frégates. |

### Verdict de l'autopsie

Le chassis V1 est un **prototype artisanal**. Il prouve que la mécanique fonctionne (OSINT → extraction → génération). Mais il n'est pas un organisme. Il est un assemblage de scripts que l'humain actionne.

Le Rubicon va conserver le moteur (OSINT, contrats, mémoire) et remplacer le système nerveux (exécution, coordination, mémoire nomade, vision stratégique, surveillance continue).

---

## III. Les Capteurs — Le Fer qui Veille

Perturabo ne dormait jamais. Ses Capteurs non plus.

### Doctrine
Avant chaque siège, Perturabo déployait un réseau de surveillance qui observait l'ennemi en continu. Pas pour attaquer — pour **comprendre**. Chaque mouvement capturé. Chaque pattern enregistré. Chaque faiblesse cataloguée.

Les Capteurs sont l'expression de cette obsession analytique appliquée au territoire YouTube.

### Ce que les Capteurs font
- **Surveillent** les chaînes concurrentes en continu (GitHub Actions, quotidien)
- **Captent** les transcriptions, métadonnées, et patterns de chaque vidéo nouvelle
- **Nourrissent** l'ARCHIVUM (la Mémoire Impériale) automatiquement
- **Alertent** le TYRANT quand un pattern viral significatif est détecté
- **Cartographient** les mouvements des démons (qui publie, quoi, quand, avec quel résultat)

### Ce que les Capteurs ne font pas
- Ils ne produisent pas de contenu (rôle des frégates)
- Ils ne décident pas (rôle du TYRANT + Warsmith)
- Ils ne analysent pas stratégiquement (rôle du TYRANT)

### Structure technique
Les Capteurs sont l'évolution du `daily_osint.yml` GitHub Actions, élevé au rang de doctrine. Ils tournent en arrière-plan, silencieux, comme le réseau de surveillance d'un siège.

```
capteurs/
├── iron_sentinel.py      # Surveillance continue des chaînes cibles
├── pattern_capture.py    # Capture et catalogage des patterns viraux
└── alert_system.py       # Alerte le TYRANT quand un signal est détecté
```

---

## IV. Les Frégates — IV Légion

Chaque frégate est un organe de la IV Légion. Nom unique. Rôle de siège unique. Dépendance claire.

### Frégate 1 : SENTINEL
**Rôle :** La Reconnaissance de Fer. Capture le specimen.
**Doctrine de siège :** Avant le siège, les Sentinelles sont envoyées en première ligne. Elles ne combattent pas — elles **voient**. Elles cartographient la forteresse, mesurent les murs, comptent les défenseurs.
**Input :** URL YouTube (fournie par le Warsmith à la Porte 1)
**Output :** Transcription + métadonnées + stats chaîne + outlier score
**Dépendance :** Aucune (premier organe activé)
**Issue du V1 :** `youtube_fetch.py` transfiguré

### Frégate 2 : BREACHER
**Rôle :** Le Briseur de Murs. Dissecte la structure du specimen et extrait le squelette viral.
**Doctrine de siège :** Les Breachers analysent les murs de la forteresse. Ils ne les détruis pas — ils trouvent les **fractures**. Le squelette viral EST la fracture. La structure cachée que tout le monde voit sans la voir.
**Input :** Transcription + `skeleton_checklist.json` + `anti_bullshit.md`
**Output :** Squelette viral structuré (JSON) — Hook, Promise, Rehooks, Body, Payoff, CTA
**Dépendance :** SENTINEL (besoin de la transcription)
**Issue du V1 :** `extract_skeleton()` extrait de `video_mode.py`

### Frégate 3 : FORGEWARD
**Rôle :** La Forge de Fer. Construit le script pour la nouvelle niche.
**Doctrine de siège :** Les Forgeward ne combattent pas sur le terrain. Ils forgent les armes de siège dans les arsenaux de la Grand Company. Le script est l'arme. Le squelette est le moule. La niche est le métal.
**Input :** Squelette viral + niche + Mémoire Impériale (rules/)
**Output :** Script complet (Audio/Vidéo) + métadonnées (titre, description, tags)
**Dépendance :** BREACHER (besoin du squelette)
**Issue du V1 :** `generate_script()` extrait de `video_mode.py`

### Frégate 4 : HERALD
**Rôle :** Le Porte-Étendard. Analyse la miniature originale et forge le concept visuel adapté.
**Doctrine de siège :** Le Herald porte l'étendard de la Grand Company. L'étendard n'est pas une décoration — c'est une arme psychologique. Il doit être vu de loin, compris en un instant, et déclencher la charge. La miniature est l'étendard.
**Input :** Thumbnail URL + nouveau titre + nouvelle niche
**Output :** Visual skeleton (JSON) + prompt Midjourney + instructions Canva + texte miniature
**Dépendance :** FORGEWARD (besoin du nouveau titre)
**Issue du V1 :** `generate_thumbnail_concept()` extraite de `video_mode.py`

### Frégate 5 : GRAND COMPASS
**Rôle :** Le Compas de la Grand Company. Cartographie les territoires adjacents et valide les océans bleus.
**Doctrine de siège :** Le Grand Compass ne regarde pas la forteresse — il regarde la **carte entière**. Où sont les autres forteresses ? Quels territoires sont vacants ? Quel démons peut être contourné au lieu d'être affronté ?
**Input :** Transcription + Mémoire Impériale + recherche web
**Output :** Rapport de niche bending (5-10 marchés) + validation océan bleu (top 3) + stratégie de lancement
**Dépendance :** SENTINEL (besoin de la transcription) + web_search
**Issue du V1 :** `channel_mode.py` éclaté et restructuré

### Frégate 6 : ARCHIVUM
**Rôle :** L'Archive de Fer. La Mémoire Impériale elle-même. Pas une frégate active — le sol sur lequel la IV Légion marche.
**Doctrine de siège :** L'ARCHIVUM est le bunker de campagne. Tout ce que les Capteurs capturent, tout ce que les frégates produisent, tout ce que le Warsmith valide — tout est stocké ici. Si le sandbox brûle, l'ARCHIVUM reconstitue la guerre.
**Input :** Règles extraites, transcriptions d'experts, artefacts produits, ledgers
**Output :** Contexte doctrinal fourni à BREACHER, FORGEWARD, GRAND COMPASS
**Dépendance :** Aucune (fondation)
**Issue du V1 :** `memory/` inchangé dans sa structure

---

## V. Les Trois Psykers

### LE TYRANT — Psyker II — L'Oracle
Perturabo, Tyrant of Olympia. Celui qui voit le territoire avant le siège.

**Identité :** Le TYRANT est un appel stratégique à un modèle de raisonnement profond (GPT-4o ou Claude 3.5 Sonnet) qui intervient **avant** que les frégates ne tournent. Il ne participe pas à la production. Il éclaire le territoire.

**Quand il est appelé :** À la **Porte 1**, après le brief du Warsmith, avant l'activation de SENTINEL.

**Ce qu'il voit :**
1. **Le territoire** : Il analyse la niche cible, sa taille, son potentiel de monétisation
2. **Le démon** : Il identifie qui domine la niche, quel est son avantage structurel, s'il a une arme secrète
3. **L'adjacent** : Il propose des territoires adjacents où le concept n'existe pas (océan bleu)
4. **L'automatisabilité** : Il estime si la niche peut être produite en série sans main humaine
5. **Les signaux des Capteurs** : Il intègre les données capturées en continu par les Capteurs

**Ce qu'il produit :** Un **Rapport d'Éclairement** (JSON) qui contient :
- `territory_analysis` : taille, audience, monétisation
- `demon_identification` : qui domine, avantage, vulnérabilité
- `adjacent_territories` : 5-10 marchés adjacents
- `automatability_score` : 1-10
- `recommended_path` : "attaque_directe" ou "ocean_bleu"
- `hunt_brief` : le brief affiné que les frégates vont exécuter

**Contrat du TYRANT :**
Reçoit : le brief du Warsmith + la Mémoire Impériale + l'`anti_bullshit.md` + les signaux des Capteurs
Ne reçoit PAS : les détails techniques d'exécution (rôle de l'IRON) ni le squelette viral (rôle de BREACHER après SENTINEL)

### L'IRON — Psyker III — L'Exécuteur
La IV Légion entre les portes. Le fer qui frappe.

**Identité :** L'IRON est le modèle LLM qui opère entre les portes. Dans PERTURABO, c'est l'API OpenAI (GPT-4o) appelée par les frégates BREACHER, FORGEWARD, HERALD et GRAND COMPASS.

**Comment il opère :**
- Il reçoit le **Grand Company Ledger** (mémoire nomadique du siège en cours)
- Il reçoit les **contrats** (skeleton_checklist, anti_bullshit, system_prompt)
- Il reçoit les **instructions** de la frégate qui l'appelle
- Il produit. Il itère. Il corrige ses propres erreurs.
- Il ne s'arrête que lorsqu'il atteint la **porte suivante**

**Ce qu'il ne fait pas :**
- Il ne prend pas de décisions stratégiques (rôle du TYRANT + Warsmith)
- Il ne valide pas le territoire (rôle du TYRANT)
- Il ne décide pas de publier (rôle du Warsmith à la Porte 4)

### LE WARSMITH — Le Champion
Nick. Le Warsmith de la Grand Company.

**Ce que le Warsmith fait :**
- Il se présente aux **quatre portes**
- Il fournit le brief initial (Porte 1)
- Il valide ou rejette à chaque porte
- Il exerce son **jugement** — pas sa technique

**Ce que le Warsmith ne fait pas :**
- Il ne code pas entre les portes
- Il ne corrige pas les frégates en temps réel
- Il ne lance pas de commandes manuelles
- Il ne debug pas

**Le serment du Warsmith :**
> *« Fer au-dedans, Fer au-dehors. Je ne touche pas au code entre les portes. Je ne corrige pas ce que l'IRON produit en temps réel. Je décide aux portes. Je tranche. Je valide ou je rejette. C'est ma seule main. Le reste est du fer. »*

---

## VI. Les Quatre Portes de Siège

Les portes sont les seuls moments d'intervention humaine. Entre les portes, l'IRON travaille. Le Warsmith ne touche pas au code. Le Warsmith ne corrige pas. Le Warsmith **décide**.

### Porte 1 : Le Brief
**Moment :** Avant le début du siège.
**Ce que le Warsmith fait :**
- Fournit l'URL du specimen
- Fournit la niche de destination (Mode Vidéo) OU demande une analyse de territoire (Mode Chaîne)
- LE TYRANT est appelé ici : il éclaire le territoire, évalue le démon, estime l'automatisabilité, intègre les signaux des Capteurs
**Ce que le Warsmith valide :** La direction du siège. Pas les détails.
**L'IRON prend le relais après :** SENTINEL → BREACHER tournent.

### Porte 2 : Le Specimen
**Moment :** Après extraction du squelette viral par BREACHER.
**Ce que le Warsmith fait :**
- Consulte le squelette extrait
- Valide : "Oui, c'est bien la structure que je veux cloner"
- Ou rejette : "Non, le hook est mal identifié, re-analyse"
**Ce que le Warsmith valide :** La structure extraite. Pas le contenu généré.
**L'IRON prend le relais après :** FORGEWARD (+ HERALD pour Mode Vidéo) tournent.

### Porte 3 : Le Blueprint
**Moment :** Après génération du script + métadonnées par FORGEWARD.
**Ce que le Warsmith fait :**
- Lit le script généré
- Valide : "Le script respecte le squelette et la niche. On continue."
- Ou demande une révision : "Le ton est trop formel. Le rehook 2 est faible. Itère."
**Ce que le Warsmith valide :** Le script et les métadonnées.
**L'IRON prend le relais après :** HERALD termine (Mode Vidéo) ou GRAND COMPASS lance la validation (Mode Chaîne).

### Porte 4 : L'Artefact
**Moment :** Après génération complète (script + miniature OU rapport de niche).
**Ce que le Warsmith fait :**
- Consulte l'artefact final
- Valide : "C'est prêt. Publication."
- Ou archive : "Pas encore. Je garde pour plus tard."
**Ce que le Warsmith valide :** L'artefact final. Le résultat du siège.
**Après :** Le Grand Company Ledger est finalisé. L'artefact est sauvegardé dans `memory/templates/`. Le siège est terminé.

---

## VII. Le Grand Company Ledger — Mémoire Nomade

Le ledger est le sang de la IV Légion. Il circule entre les frégates, entre les sessions, entre les sandboxes.

### Structure

```json
{
  "siege_id": "perturabo_2026_07_08_001",
  "mode": "video | channel",
  "status": "gate_1 | gate_2 | gate_3 | gate_4 | completed",
  "warsmith_brief": {
    "video_url": "...",
    "niche": "...",
    "intent": "..."
  },
  "tyrant_report": {
    "territory_analysis": "...",
    "demon_identification": "...",
    "recommended_path": "...",
    "hunt_brief": "...",
    "capteur_signals": "..."
  },
  "sentinel_output": {
    "transcript": "...",
    "metadata": {...},
    "outlier_score": ...
  },
  "breacher_output": {
    "skeleton": {...},
    "analysis_notes": "..."
  },
  "forgeward_output": {
    "title": "...",
    "script": [...],
    "metadata": {...}
  },
  "herald_output": {
    "visual_skeleton": {...},
    "midjourney_prompt": "...",
    "thumbnail_text": "..."
  },
  "grand_compass_output": {
    "niche_proposals": [...],
    "blue_ocean_validations": [...],
    "recommended_niche": "..."
  },
  "gate_decisions": {
    "gate_1": {"validated": true, "timestamp": "..."},
    "gate_2": {"validated": true, "timestamp": "...", "notes": "..."},
    "gate_3": {"validated": false, "revision_request": "..."},
    "gate_4": {"validated": true, "timestamp": "..."}
  },
  "created_at": "...",
  "updated_at": "..."
}
```

### Règles du Grand Company Ledger
1. **Un siège = un ledger.** Pas de ledger global. Pas de mémoire partagée entre sièges.
2. **Le ledger voyage.** Si le sandbox brûle, le ledger reconstitue le contexte en quelques secondes.
3. **Le ledger est immuable entre les portes.** L'IRON peut lire mais pas modifier les décisions de portes.
4. **Le ledger est la seule source de vérité.** Si une frégate produit quelque chose qui n'est pas dans le ledger, ça n'existe pas.

---

## VIII. L'Orchestrateur

L'Orchestrateur est le nerf central de la IV Légion. Il connaît l'état de chaque frégate. Il décide l'ordre d'exécution. Il gère les reprises après échec.

### Identité
L'Orchestrateur est le `main.py` transfiguré. Il ne fait plus des appels CLI manuels — il **orchestre** le flux entre les portes.

### Responsabilités
1. **Initialiser le siège** : créer le Grand Company Ledger, appeler LE TYRANT (Porte 1)
2. **Activer les frégates** dans l'ordre entre les portes
3. **Présenter les portes** au Warsmith (afficher le squelette, le script, l'artefact)
4. **Enregistrer les décisions** du Warsmith dans le ledger
5. **Gérer les reprises** : si une frégate échoue, l'Orchestrateur relance ou signale
6. **Finaliser** : sauvegarder l'artefact dans `memory/templates/`, marquer le ledger comme `completed`

### Flux Mode Vidéo
```
[Porte 1: Brief] → TYRANT → SENTINEL → BREACHER → [Porte 2: Specimen] → FORGEWARD → HERALD → [Porte 3: Blueprint] → [Porte 4: Artefact]
```

### Flux Mode Chaîne
```
[Porte 1: Brief] → TYRANT → SENTINEL → GRAND COMPASS → [Porte 2: Territoire] → FORGEWARD (premier script) → [Porte 3: Blueprint] → [Porte 4: Artefact]
```

---

## IX. La Séquence de Greffe

Le Rubicon s'exécute dans cet ordre. Pas de raccourci.

### Phase 1 : Mutation des Contrats
1. Réécrire `system_prompt.md` pour intégrer la doctrine complète (rôles, portes, ledger, capteurs, IV Légion)
2. Créer `contracts/tyrant_prompt.md` — le contrat spécifique du TYRANT
3. Créer `contracts/iron_prompt.md` — le contrat spécifique de l'IRON
4. `skeleton_checklist.json` et `anti_bullshit.md` survivent inchangés

### Phase 2 : Les Capteurs
5. Créer `src/capteurs/iron_sentinel.py` — surveillance continue des chaînes concurrentes
6. Créer `src/capteurs/pattern_capture.py` — capture et catalogage des patterns viraux
7. Créer `src/capteurs/alert_system.py` — alerte le TYRANT quand un signal significatif est détecté
8. Transfigurer `daily_osint.yml` → `iron_sentinel.yml` (GitHub Actions pour les Capteurs)

### Phase 3 : Éclatement en Frégates
9. Extraire `extract_skeleton()` de `video_mode.py` → `src/fregates/breacher.py`
10. Extraire `generate_script()` de `video_mode.py` → `src/fregates/forgeward.py`
11. Extraire `generate_thumbnail_concept()` de `video_mode.py` → `src/fregates/herald.py`
12. Restructurer `channel_mode.py` → `src/fregates/grand_compass.py`
13. Transfigurer `youtube_fetch.py` → `src/fregates/sentinel.py`
14. Chaque frégate : input → output → pas de logique de coordination interne

### Phase 4 : Le Grand Company Ledger
15. Créer `src/ledger.py` — gestion du ledger (création, lecture, écriture, reprise)
16. Le ledger est sauvegardé dans `memory/ledgers/` (un fichier par siège)

### Phase 5 : Le TYRANT
17. Créer `src/tyrant.py` — l'appel stratégique pré-siège
18. LE TYRANT lit la Mémoire Impériale + le brief du Warsmith + les signaux des Capteurs
19. LE TYRANT produit le Rapport d'Éclairement

### Phase 6 : L'Orchestrateur
20. Réécrire `main.py` → `src/orchestrator.py`
21. L'Orchestrateur gère le flux : Porte 1 → frégates → Porte 2 → frégates → Porte 3 → Porte 4
22. L'Orchestrateur présente chaque porte au Warsmith (interface CLI interactive ou Streamlit)

### Phase 7 : Les Portes de Siège
23. Implémenter la logique de porte : pause → présentation → validation/rejet → enregistrement dans le ledger
24. Si rejet à une porte : l'Orchestrateur relance la frégate concernée avec les notes du Warsmith

### Phase 8 : Validation Rubicon
25. Test binaire : PERTURABO produit le même artefact que la V1 manuelle, sans main humaine entre les portes
26. Si oui → le Rubicon est traversé. PERTURABO est Primaris.
27. Si non → identifier la porte qui échoue, corriger, re-valider

---

## X. Validation — Le Test du Rubicon

Le test est binaire. Pas "à peu près". Pas "presque".

### Critère
> PERTURABO reçoit un brief à la Porte 1. Le Warsmith ne touche rien entre les portes. À la Porte 4, l'artefact produit est de la même qualité que ce que la V1 manuelle produisait avec intervention humaine à chaque étape.

### Procédure de test
1. Lancer PERTURABO en Mode Vidéo avec une URL + une niche
2. Valider les 4 portes sans modifier le travail des frégates
3. Comparer l'artefact final avec un artefact produit par la V1 manuelle sur les mêmes inputs
4. Si l'artefact PERTURABO est égal ou supérieur → **Rubicon traversé**
5. Si inférieur → identifier la frégate défaillante, corriger, re-tester

### L'irréversibilité
Après validation, l'ancien `main.py` CLI est supprimé. Il n'y a pas de retour. L'outil n'est plus "manuel avec option automation". Il est "autonome avec quatre moments d'intervention humaine".

Ce sont deux natures différentes. Le fer ne redevient pas du minerai.

---

## XI. La Structure Transfigurée

```
perturabo/
├── memory/                          # ARCHIVUM — La Mémoire Impériale
│   ├── transcripts/                 # Transcriptions capturées par les Capteurs
│   ├── rules/                       # Règles d'or extraites et validées
│   ├── templates/                   # Artefacts produits (scripts générés)
│   └── ledgers/                     # Grand Company Ledgers (un par siège)
│
├── contracts/                       # CONTRATS DE L'IA
│   ├── system_prompt.md             # Doctrine complète (muté)
│   ├── tyrant_prompt.md             # Contrat spécifique du TYRANT (nouveau)
│   ├── iron_prompt.md               # Contrat spécifique de l'IRON (nouveau)
│   ├── skeleton_checklist.json      # Checklist d'extraction (survit)
│   └── anti_bullshit.md             # Filtre anti-fausses règles (survit)
│
├── src/
│   ├── capteurs/                    # LES CAPTEURS — Le Fer qui Veille
│   │   ├── iron_sentinel.py         # Surveillance continue des concurrents
│   │   ├── pattern_capture.py       # Capture et catalogage des patterns
│   │   └── alert_system.py          # Alerte le TYRANT sur signaux significatifs
│   │
│   ├── fregates/                    # LES FRÉGATES — IV Légion
│   │   ├── sentinel.py              # Reconnaissance OSINT — capture le specimen
│   │   ├── breacher.py              # Briseur de murs — extrait le squelette viral
│   │   ├── forgeward.py             # Forge de fer — génère le script
│   │   ├── herald.py                # Porte-Étendard — génère le concept miniature
│   │   └── grand_compass.py         # Compas — niche bending + océan bleu
│   │
│   ├── tyrant.py                    # LE TYRANT — Vision pré-siège (Psyker II)
│   ├── ledger.py                    # LE GRAND COMPANY LEDGER — Mémoire nomade
│   ├── orchestrator.py              # L'ORCHESTRATEUR — Nerf central
│   └── gates.py                     # LES PORTES DE SIÈGE — Intervention humaine
│
├── .github/workflows/
│   └── iron_sentinel.yml            # Capteurs automatisés (surveillance continue)
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## XII. Le Calendrier du Rubicon

| Phase | Durée estimée | Livrable |
|---|---|---|
| Phase 1 : Mutation des contrats | 30 min | `system_prompt.md` réécrit + `tyrant_prompt.md` + `iron_prompt.md` |
| Phase 2 : Les Capteurs | 45 min | `iron_sentinel.py` + `pattern_capture.py` + `alert_system.py` |
| Phase 3 : Éclatement en frégates | 1h | 5 frégates indépendantes dans `src/fregates/` |
| Phase 4 : Le Grand Company Ledger | 30 min | `src/ledger.py` fonctionnel |
| Phase 5 : Le TYRANT | 45 min | `src/tyrant.py` fonctionnel |
| Phase 6 : L'Orchestrateur | 1h | `src/orchestrator.py` gère le flux complet |
| Phase 7 : Les Portes de Siège | 45 min | `src/gates.py` + interface de validation |
| Phase 8 : Validation | 30 min | Test binaire du Rubicon |
| **Total** | **~5h30** | **PERTURABO Primaris** |

---

## XIII. La Nomenclature — Table de Correspondance

| V1 (youtube-mcp) | PERTURABO | Rôle |
|---|---|---|
| Projet "youtube-mcp" | **PERTURABO** | L'organisme entier |
| `main.py` CLI | **Orchestrateur** | Nerf central |
| `video_mode.py` | **BREACHER + FORGEWARD + HERALD** | Trois frégates séparées |
| `channel_mode.py` | **GRAND COMPASS** | Une frégate |
| `youtube_fetch.py` | **SENTINEL** | Frégate de reconnaissance |
| `web_search.py` | (intégré à GRAND COMPASS) | Recherche web |
| `extract_skeleton()` | **BREACHER** | Extraction du squelette |
| `generate_script()` | **FORGEWARD** | Génération du script |
| `generate_thumbnail_concept()` | **HERALD** | Génération miniature |
| Oracle (concept nouveau) | **LE TYRANT** | Vision pré-siège |
| Exécuteur (concept nouveau) | **L'IRON** | Exécution entre portes |
| Champion (concept nouveau) | **LE WARSMITH** | Décision aux portes |
| Ledger (concept nouveau) | **GRAND COMPANY LEDGER** | Mémoire nomade |
| Capteurs (concept nouveau) | **LES CAPTEURS** | Surveillance continue |
| `daily_osint.yml` | **iron_sentinel.yml** | GitHub Actions des Capteurs |
| `memory/` | **ARCHIVUM** | Mémoire Impériale |
| `system_prompt.md` | **system_prompt.md** (muté) | Doctrine |
| — | **tyrant_prompt.md** (nouveau) | Contrat du TYRANT |
| — | **iron_prompt.md** (nouveau) | Contrat de l'IRON |
| `skeleton_checklist.json` | **skeleton_checklist.json** (survit) | Checklist |
| `anti_bullshit.md` | **anti_bullshit.md** (survit) | Filtre |

---

*LE RUBICON — Plan de Transfiguration*
*PERTURABO — Version 1.0 → Primaris*
*IV Légion — Iron Warriors*
*« Fer au-dedans, Fer au-dehors. »*
*Media Pipeline Architecture — Territoire YouTube*
*Accès restreint — ne circule pas*
