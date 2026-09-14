# 05_NOTE_PERTURABO_PACK_MEME — Note de format à l'attention de PERTURABO

> Note envoyée par **LACRIMAE** (le projet qui consomme le pack, successeur
> d'OMNIS_WATCH — il en fait exactement la même chose : monter la vidéo depuis
> le pack). Cette note fait foi sur le format du pack meme.
> PERTURABO doit la suivre à la lettre.

---

## 1. Objet

Ce document précise les corrections **v2.5** du pack meme. Il complète le
contrat de montage `04_MODE_MEME.md` (doctrine 6 couches) référencé par le
pack via `meme_source.montage_guide_ref`.

## 2. Rappel : référence de la méméthèque

Le champ `meme` d'une vidéo du pack doit pointer vers **les fichiers existants
de la méméthèque LACRIMAE** :

| Valeur attendue | Commentaire |
|---|---|
| `meme_001` | format de meme n°1 historique |
| `meme_002` | format de meme n°2 historique |
| `M1` | balise de release mème validée par le Champion ; sa signification opérationnelle est définie dans le pack du siège |

> ⚠️ Ne pas utiliser `meme_1` / `meme_2` comme identifiants de bibliothèque. Les identifiants historiques `meme_001` / `meme_002` restent valides lorsqu’ils existent dans la méméthèque ; une balise de release comme `M1` est valide lorsqu’elle est explicitement choisie par le Champion et inscrite dans le pack.

## 3. Le champ `tweet` d'une vidéo meme

| Champ | Règle |
|---|---|
| `tweet.text` | fake tweet, **max 3 lignes**, affiché comme faux post quart haut |
| `tweet.keywords_style` | coloration des mots-clés — voir **section 4** |
| `text_emotion` | texte d'émotion au milieu, **max 4 mots** |
| `emotion` | l'émotion de l'angle |
| `duration_sec` | durée du clip en secondes (plage 5-30, défaut 8) |

## 4. Les couleurs (`tweet.keywords_style`) — RÈGLES LACRIMAE

### Règle 1 — FORMAT : un dict, PAS une liste

`tweet.keywords_style` doit être un **dict** à clés anglaises :

```json
{
  "keywords_style": {
    "green": ["degree"],
    "red": ["loans", "interest"]
  }
}
```

- Clés autorisées : `green` (valeur positive) et `red` (danger/négatif).
- **Une liste `[{word, color}]` → AUCUNE couleur** : LACRIMAE n'appliquera
  alors aucune coloration sur le tweet. PERTURABO ne doit donc **jamais**
  produire une liste.

### Règle 2 — MOTS : un seul mot, présent dans `tweet.text`

Chaque entrée de `green` / `red` doit être **un mot seul**, présent dans
`tweet.text` :

- Comparaison **mot à mot**, ponctuation ignorée (les apostrophes, virgules,
  `$`, `#`… ne comptent pas).
- **Les phrases multi-mots ("student loans", "owe more") ne matcheront
  jamais** — elles doivent être découpées en mots simples (`loans`, `owe`).

### Exemple conforme

Tweet :

```
Took out $50K in student loans for a degree
Nobody told me the interest would double it
Now I owe more than my parents' mortgage
```

keywords_style conforme :

```json
{
  "keywords_style": {
    "green": ["degree"],
    "red": ["loans", "interest"]
  }
}
```

## 5. Liste de contrôle pour PERTURABO

- [ ] `meme` = une balise existante et validée par le Champion ; pour le siège New York Bagel, la balise est `M1`
- [ ] ne pas confondre une balise de release de siège (`M1`) avec un ancien identifiant de bibliothèque (`meme_001`)
- [ ] `keywords_style` = dict `{"green": [...], "red": [...]}` (jamais une liste)
- [ ] chaque mot de `green`/`red` est **un mot seul** présent mot à mot dans `tweet.text`
- [ ] pas de phrase multi-mots dans les couleurs


## 6. Texte motion contextualisé

Le champ `text_emotion` est une réaction courte placée au milieu de la vidéo. Il doit identifier les personnes réellement présentes dans le fake tweet et se terminer par `:`. Exemples : `My sister and me right now:`, `The two neighbors right now:` ou `My roommate and me right now:`. Les formes génériques, les marqueurs `A:` / `B:`, les personnages absents et les résidus d’un autre siège sont interdits.

Le texte motion ne doit pas être copié mécaniquement d’un angle à l’autre. Le contexte, la relation et le ressort comique doivent être contrôlés angle par angle afin d’éviter le cannibalisme de forme.

## 7. Validation de release

F05 assemble le pack, mais ne décide pas de la Gate. Le Champion examine les dix tweets, les dix textes motion, les métadonnées et la balise mème avant l’export. La copie dans `EXPORT/` et l’expédition à LACRIMAE ne sont permises qu’après cette validation explicite.

La clé premium sert à la génération éditoriale lorsqu’elle est activée ; F05 reste un assembleur déterministe et ne doit pas simuler un appel premium.

## 8. Contrat MEME V2 : source et transformation

Le pack ne doit plus traiter le post original comme un tweet PERTURABO. Les deux contenus sont séparés :

| Champ | Contenu | Règle |
|---|---|---|
| `source_post.text` | Copie fidèle du tweet ou post Reddit choisi par le Champion | Input interne F01 ; archivé pour traçabilité, pas une couche obligatoire du pack final |
| `source_post.screenshot` | Capture originale lisible | Conservée comme preuve et fournie à LACRIMAE |
| `source_post.url` | URL publique | Obligatoire lorsque disponible |
| `source_post.author` | Auteur, compte ou subreddit | Ne pas inventer |
| `source_post.observed_at` | Date et heure d’observation | Conserver l’horodatage |
| `source_post.metrics` | Likes, vues, commentaires, reposts ou score | Valeurs observées ; les inconnues restent inconnues |
| `reaction_tweet` | Réaction originale PERTURABO | Doit apporter une lecture, une tension ou une chute ; la paraphrase seule est interdite |
| `text_emotion` | Motion court | Dérivé du contexte de réaction, sans résidu d’un autre siège |
| `metadata` | Titre, description et tags | Dérivés de la source et de la réaction, sans promesse automatique de fair use ou de monétisation |

La capture PNG de la source affichée et la réaction doivent être visuellement distinctes dans le pack. Le pack doit permettre à LACRIMAE de montrer clairement ce qui provient du post original et ce qui constitue la contribution créative de PERTURABO. La copie textuelle complète reste interne à F01 et n’est pas une couche de rendu obligatoire.

## 9. Puissance et anti-cannibalisation

Le `reaction_tweet` est la pièce stratégique principale. Chaque réaction doit viser le `market_target` déclaré et posséder un point de vue identifiable. Dix réactions qui changent seulement le vocabulaire, le personnage ou la ponctuation sont une cannibalisation et doivent être refusées.

Pour une même source, plusieurs angles ne sont acceptables que si la tension, la lecture, le public visé ou le ressort comique changent réellement. F04 doit enregistrer `reaction_angle` afin que la diversité puisse être contrôlée avant F05.

## 10. Vision et conformité

Un modèle de vision n’est pas obligatoire lorsque F01 reçoit la copie textuelle du post. Une vérification visuelle ou OCR peut être activée uniquement pour contrôler la lisibilité et la correspondance entre la capture et le texte fourni. La capture ne constitue pas à elle seule une autorisation de réutilisation ; la transformation, l’attribution et la conformité aux règles de la plateforme doivent être examinées avant publication.

F05 assemble les champs validés et ne réécrit ni la source ni la réaction.


## 11. Correction finale du pack MEME V2

La copie textuelle (`source_post.text`) est un input interne de F01 pour comprendre la source sans modèle de vision obligatoire. Elle reste archivée pour la traçabilité, mais ne doit pas être envoyée comme couche textuelle obligatoire au pack final.

La capture (`source_post.screenshot_png`) contient déjà le tweet et son image. Elle est obligatoire dans le pack final et doit être affichée au-dessus de la vidéo mème par LACRIMAE. Le pack transmet aussi le clip mème par `clip_id`, son `meme_tag` et la chaîne opérateur par `channel_id`.

Le contrat d’export est donc : capture PNG + clip mème référencé + reaction_tweet + text_emotion + métadonnées + tag + chaîne. F05 assemble ces éléments ; LACRIMAE produit la vidéo finale. La valeur `source_post.text` ne doit pas devenir une couche de rendu séparée.
