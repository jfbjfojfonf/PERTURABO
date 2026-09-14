# 04_MODE_MEME — Guide complet

> **MODE MEME V2** : le Champion fournit un tweet ou post Reddit réel avec sa copie
> textuelle et sa capture → F01 archive et contrôle la source → ANGLESMITH propose
> des angles de réaction → F04 forge pour chaque angle un **reaction_tweet puissant**,
> un `text_emotion` contextualisé et les métadonnées → F05 assemble un pack avec
> la source et la transformation → la release est revue par le Champion puis
> transmise à **LACRIMAE**, qui réalise la vidéo.
>
> F00 est en pause dans ce mode et ne fabrique plus de sujets à partir d’un mot-clé.
> La source originale et la réaction PERTURABO sont toujours deux champs distincts.
>
> Doctrine issue de la dissection visuelle du démon @zdak (Kimi K3, rapport
> `answers/question-2026-08-15-02.md` du repo Scriptorum).
>
> ⚠️ **Ce guide EST le contrat de montage.** Le pack meme référence
> `montage_guide_ref: "GUIDE_UTILISATION/04_MODE_MEME.md"` — LACRIMAE le
> charge pour rendre la vidéo.

---

## 🎯 Le but en 3 lignes

1. Tu fournis un **post réel** : copie textuelle, capture, URL, auteur, date et métriques disponibles.
2. Le forge analyse la source puis propose jusqu’à **10 angles de réaction** réellement distincts.
3. Chaque angle reçoit un **reaction_tweet puissant** (maximum 3 lignes), un `text_emotion` court et contextualisé, une émotion et des métadonnées dérivées de la source et de la réaction.
4. **LACRIMAE** monte chaque vidéo selon la doctrine ci-dessous et poste ; les vues sont suivies par F06.

---

## 🧾 Les inputs (ce que TU fournis)

| Fichier | Rôle | Exemple |
|---|---|---|
| `keyword.txt` | Le **mot-clé** du siège | `westbrook retirement` |
| `directive.md` | Le brief de la campagne | `MEME MODE: keyword ...` |

> ⚠️ **Mode MEME V2** : F00 est en pause. F01 reçoit une source manuelle complète :
> `source_post.text`, `source_post.screenshot`, `source_post.url`, auteur, date et
> métriques disponibles. F01 ne nécessite pas de vision si la copie textuelle est
> fournie ; il contrôle la cohérence et archive la preuve. F03 reste ignorée : aucun
> clip n’est chassé et aucun segment n’est sélectionné.

---

## 🗺️ Le chemin complet — les gates avec commandes EXACTES

### Étape 0 — Ouvrir le siège

```bash
cd MONDES_FORGES/CLIPPING/ORCHESTRATOR/CODEBASE
python3 orchestrator.py --start-siege
```

---

### 🚪 GATE 1 — F01 : intake et validation de la source manuelle

**Frégate** : `F01_SCOUT` — archive et contrôle la source fournie par le Champion, sans télécharger de clip.

```text
source_post.text       = copie exacte du tweet ou post Reddit
source_post.screenshot = capture originale lisible
source_post.url        = URL publique de la source
source_post.author     = auteur ou subreddit
source_post.observed_at = date/heure d’observation
source_post.metrics    = vues, likes, commentaires, reposts ou score disponibles
```

**Sortie** : `F01_SCOUT/OUT/source_post_<source_id>.json` (+ capture archivée et résumé de contrôle)

| Champ | Signification |
|---|---|
| `source_post.text` | copie textuelle exacte du post |
| `source_post.screenshot` | capture utilisée comme preuve visuelle |
| `source_post.url` | URL de provenance |
| `source_post.author` | auteur, compte ou subreddit |
| `source_post.observed_at` | horodatage de collecte |
| `source_post.metrics` | métriques observées, avec valeurs manquantes conservées |
| `source_post.provenance_status` | `verified`, `review` ou `blocked` |

**Ce que F00 ne fait PAS** : télécharger la vidéo, fournir un clip, inventer
une stat. `signal_vues_youtube` = stats réelles de l'API YouTube.

**Validation** :
```bash
cd ../../ORCHESTRATOR/CODEBASE
python3 orchestrator.py --gate 1 --decision valide --notes "viralité multi-sources pour keyword OK, aucun clip téléchargé"
```

---

### 🚪 GATE 2 — Les angles (ANGLESMITH, mode meme)

**Frégate** : `F02_TYRANT_CAMP` (ANGLESMITH) — forge jusqu’à 10 angles, avec contrôle anti-cannibalisation.

```bash
cd ../../F02_TYRANT_CAMP/CODEBASE
python3 anglesmith.py --auto --n-angles 10 --sub-mode meme
# présenter les angles au Champion ; ne pas finaliser avant sa décision
```

**Sortie** : `F02_TYRANT_CAMP/OUT/angles.json`

Chaque angle porte en plus du schéma standard :
| Champ | Règle |
|---|---|
| `emotion` | l'émotion de l'angle (ex : poignant, drôle, choc, émerveillé, tendu) |
| `duration_sec_range` | fourchette conseillée (défaut 5-7s) |

**Règle anti-spam sur les émotions** : une même émotion ne peut couvrir que
**2 angles max** sur les 5 — les 3 autres doivent être différentes. La règle
de voisinage est douce (pas 2 mêmes émotions côte à côte).

**Validation** :
```bash
cd ../../ORCHESTRATOR/CODEBASE
python3 orchestrator.py --gate 2 --decision valide --notes "5 angles meme forgés, anti-spam émotions OK"
```

---

### 🚪 GATE 3 — Les textes (F04 COPYWRITER, mode meme)

**Frégate** : `F04_COPYWRITER` — forge les text_payloads meme des angles validés.

Pour CHAQUE angle (A01 → A10) :

```bash
cd ../../F04_COPYWRITER/CODEBASE
python3 copywriter.py --setup-context --angle A01 --sub-mode meme
python3 copywriter.py --generate --angle A01 --sub-mode meme   # AVEC clé premium
# présenter le tweet, le text_emotion et les métadonnées au Champion
# ne lancer --ordonnance/--finalize qu’après validation explicite
```

**Sortie** : `F04_COPYWRITER/OUT/text_payload_raw_A0X.json` pendant la revue ; le payload final ne peut être créé qu’après validation du Champion.

| Champ du payload | Règle verrouillée |
|---|---|
| `title` (titre en haut) | **si nécessaire**, ≤ 6 mots, jamais de clickbait vide |
| `tweet.text` (fake tweet) | **max 3 lignes**, format post X/Twitter |
| `text_emotion` (motion central) | **max 4 mots**, réaction cohérente avec les personnes du tweet et terminée par `:` |
| `emotion` | l'émotion de l'angle, ajustable par le Champion |
| `metadata` | titre, description et tags dérivés du tweet, sans ancien sujet résiduel |
| `duration_sec` | durée entière, normalement 5–7 secondes selon le guide de montage |

> 🧙 Si la clé premium est absente : `--generate --oracle` → l'Oracle (l'assistant)
> forge `F04_COPYWRITER/OUT/text_payload_raw_<angle>.json`, puis relance
> `--generate --oracle` (détecte le raw).

**Validation** :
```bash
cd ../../ORCHESTRATOR/CODEBASE
python3 orchestrator.py --gate 3 --decision valide --notes "5 textes meme validés (tweet<=3 lignes, reaction<=4 mots)"
```

---

### 🚪 GATE 4 — Le pack assemblé → validation Champion → EXPORT → LACRIMAE

**Frégate** : `F05_PACKAGER` — assembleur déterministe ; il ne sollicite pas la clé premium.

```bash
cd ../../F05_PACKAGER/CODEBASE
python3 packager.py --assemble --sub-mode meme --finalize
```

**Sortie** : `F05_PACKAGER/OUT/production_pack_logo.json` en V1 ; en V2, le pack contient le bloc `meme_v2` et les entrées `videos[*].source_post`, `reaction_tweet`, `text_emotion`, `metadata`, `clip_id`, `meme_tag` et `channel_id`.

En V1, le pack contient `sub_mode: "meme"` et les champs historiques. En V2, chaque entrée porte la capture PNG de `source_post`, le `reaction_tweet`, le `text_emotion`, les métadonnées, le `clip_id`, le `meme_tag` et le `channel_id`. La copie textuelle complète du post reste interne à F01 ; LACRIMAE reçoit la capture comme preuve visuelle et la place au-dessus du clip mème.

**Après validation explicite du Champion seulement — Expédition :**

```bash
cd MONDES_FORGES/CLIPPING
cp F05_PACKAGER/OUT/production_pack_logo.json EXPORT/production_pack_meme_<siege>.json
```

**Validation** :
```bash
cd ../../ORCHESTRATOR/CODEBASE
python3 orchestrator.py --gate 4 --decision valide --notes "pack meme conforme → LACRIMAE (monte via 04_MODE_MEME.md)"
```

---

## 🧠 RÈGLES ÉDITORIALES ANTI-CANNIBALISATION

Chaque angle doit raconter un contexte distinct : relation, lieu, déclencheur et chute doivent varier. Dix formulations du même gag ne constituent pas dix angles. Le tweet doit ressembler à une publication humoristique autonome, sans marqueurs de dialogue `A:` / `B:`. Le champ `text_emotion` doit identifier la réaction des personnes réellement présentes dans le tweet, par exemple `My sister and me right now:` ou `The two neighbors right now:`. Il ne doit jamais conserver un personnage, un sujet ou une formule provenant d’un autre siège.

Le Champion est l’unique autorité des Gates. Oracle peut signaler un défaut et suggérer une correction, mais ne peut ni valider ni rejeter une Gate à sa place.

## 🎬 LA DOCTRINE DE MONTAGE EN 6 COUCHES (ce que LACRIMAE lit dans CE guide)

> Source : dissection visuelle du démon @zdak (2.42M abonnés, 9.56 Mds vues).
> La vidéo cible "This Teacher MIGHT Be Picasso" : 5.6s, zéro dialogue, muet-compréhensible.

### Couche 1 — SETUP / FAUX POST (quart haut, fixe)
- Le faux post (tweet) est affiché dans le **quart supérieur**, **fixe** (pas d'animation).
- **Max 1.5 ligne** visible. Mots-clés **colorés** : vert (valeur) / rouge (danger).
- Le titre en haut (si présent) est court : max 1.5 ligne.

### Couche 2 — PREUVE VISUELLE (card dès la première frame)
- Une **card lumineuse** (le "proof") apparaît dès la **frame 1** — rien d'attendu :
  tout est visible immédiatement.
- Card = l'image/le visuel qui prouve le post.

### Couche 3 — LABEL NARRATIF (un seul mot change)
- Format : `[sujet] at [A]:` → `[sujet] at [B]:`
- **Un seul mot change** entre la version A et la version B (~50% par version).
- Exemple démon : "this teacher at school:" → "this teacher at home:" — tout le
  contexte est posé en changeant UN mot.

### Couche 4 — RÉACTEUR ÉMOTIONNEL (contraste extrême)
- 2 clips d'une **même œuvre pop-culture** au contraste extrême (ex : All Quiet —
  un homme pleure → le même homme danse).
- C'est la **méta-blague** : le réacteur visuel exprime l'émotion du post.

### Couche 5 — TRANSITION-PIVOT (flash/cut sec + impact sonore)
- La bascule A→B se fait par **flash ou cut sec** + **impact sonore**.
- Positionné à **50-55% du runtime** (≈ 3s sur 5.6s).

### Couche 6 — WATERMARK (semi-transparent, bas-gauche)
- Watermark du logo en **semi-transparent**, **bas-gauche**.

### Règles d'assemblage (non négociables)
| Règle | Valeur |
|---|---|
| Durée | **5-7s max** |
| Premier visuel | **tout visible dès frame 1** |
| Nombre de bascules | **une seule** (A→B) |
| Son | muet-compréhensible (impact sonore OK) |
| Mouvement | **un seul objet en mouvement** par moment |
| Boucle | boucle invisible en bonus |
| Ratio | 9:16 (1080×1920) |
| Logo | image transparente campagne, bas-gauche |

---

## ⚙️ Les règles verrouillées (garde-fous mode meme)

| Règle | Valeur |
|---|---|
| Titre en haut | **si nécessaire**, ≤ 6 mots |
| Fake tweet | **max 3 lignes** |
| Texte d'émotion (milieu) | **max 4 mots** |
| Émotion anti-spam | une émotion = **2 angles max** sur les 10, sauf décision explicite du Champion |
| Durée | **5-7s** |
| F01 / F03 | **SKIP** en mode meme (pas de timecodes, pas de segments) |
| Pas de clip à télécharger | F00 scanne les stats, jamais le contenu |
| Balise mème | une balise validée par le Champion, par exemple `M1`, commune ou distincte selon la décision du siège |
| URL de meme dans le pack | **interdit** (les sources restent dans `meme_source.virality_scan`) |

---

## ✅ Checklist rapide

- [ ] `keyword.txt` déposé · [ ] Gate 1 : viralité multi-sources (0 clip téléchargé)
- [ ] Gate 2 : jusqu’à 10 angles, contextes distincts, anti-cannibalisation contrôlée
- [ ] Gate 3 : tweet ≤ 3 lignes, text motion ≤ 4 mots, personnages cohérents, métadonnées propres
- [ ] Gate 4 : pack `sub_mode: meme` + `montage_guide_ref` + balise mème + validation Champion + copié dans EXPORT/

---

👉 **Prochaine étape après le siège** : `F06_TRACKER` — `python3 tracker.py --post`
une fois les vidéos publiées (suit vues 1h/24h, payout, learnings).


## MODE MEME V1 OU V2 — QUESTION OBLIGATOIRE D’ORACLE

Quand le Champion dit « entre en mode meme », Oracle doit demander avant toute action :

> **MEME V1 ou MEME V2 ?**

**MEME V1** conserve le flux historique par mot-clé : F00 Discovery, angles, F04, F05. **MEME V2** utilise une source sociale fournie manuellement : F00 est en pause, F01 archive la source, F02/ANGLESMITH analyse et forge, F04 crée la réaction originale, le motion et les métadonnées, puis F05 assemble.

Oracle doit conserver la version choisie dans le contexte du siège et la répéter dans chaque compte rendu. Une version ne peut pas être changée en cours de siège sans décision explicite du Champion.

## ORACLE CONDUIT MEME V2 JUSQU’AU BOUT

En V2, Oracle guide le Champion dans cet ordre strict :

| Étape | Action Oracle | Décision Champion |
|---:|---|---|
| 1 | Demander `source_post.text`, capture, URL, auteur, date et métriques | Fournir et valider la source à Gate 1 |
| 2 | Faire préparer et contrôler F01 | Valider ou rejeter la provenance |
| 3 | Faire analyser la tension, le marché et le potentiel | Autoriser la forge des angles |
| 4 | Faire forger les angles anti-cannibalisation | Valider ou rejeter à Gate 2 |
| 5 | Faire générer le `reaction_tweet` puissant | Examiner le texte réaction |
| 6 | Générer le `text_emotion` depuis le contexte | Examiner le motion et les métadonnées à Gate 3 |
| 7 | Faire assembler F05 avec source et transformation séparées | Valider ou rejeter le pack à Gate 4 |
| 8 | Exporter et fermer le siège | Donner l’ordre explicite d’export puis de fermeture |

Oracle présente toujours la sortie avant de demander la décision. Il ne lance jamais l’étape suivante en anticipant une validation, ne réutilise aucun résidu d’un autre siège et ne confond jamais la source originale avec la réaction PERTURABO.


## MEME V2 — contrat d’asset final corrigé

La copie du tweet ou post Reddit est fournie à F01 pour analyse interne et provenance. Elle n’est pas une couche textuelle obligatoire du pack final. La capture PNG, qui contient déjà le tweet et son image, est en revanche un asset obligatoire du pack final : LACRIMAE l’affiche au-dessus du clip mème.

Le clip mème provient de la release LACRIMAE et est référencé par `clip_id` et `meme_tag`. L’Opérateur fournit `meme_tag` et `channel_id` pour chaque angle. F05 assemble la capture, la référence du clip, le `reaction_tweet`, le `text_emotion` et les métadonnées ; LACRIMAE fabrique le rendu final sans inventer ni réécrire ces éléments.
