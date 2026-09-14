# Note technique — Intégration LACRIMAE / PERTURABO MEME V2

**Version :** 2.0  
**Statut :** contrat d’intégration opérationnel  
**Producteur :** PERTURABO / CLIPPING  
**Consommateur :** LACRIMAE  
**Mode :** `logo` + `meme_v2`  
**Dernière révision :** 2026-08-24

> Cette note décrit le contrat de remise entre PERTURABO et LACRIMAE pour les vidéos MEME V2. Elle ne décrit pas une génération de contenu source : la source sociale est choisie et fournie manuellement par le Champion. PERTURABO produit la transformation éditoriale ; LACRIMAE réalise le rendu audiovisuel final.

## 1. Décision d’architecture

MEME V2 remplace la recherche automatique de scénarios inventés par une chaîne **source réelle → réaction originale → rendu mème**. Le Champion fournit à PERTURABO une copie textuelle du post, une capture PNG, l’URL, l’auteur, la date d’observation et les métriques disponibles. F01 utilise la copie textuelle pour contrôler et archiver la provenance ; il n’est pas nécessaire d’utiliser un modèle de vision pour comprendre la source lorsque la copie textuelle est fournie.

La capture PNG a cependant une fonction différente : elle constitue la **preuve visuelle de production**. Elle contient déjà le tweet ou le post, ainsi que son image éventuelle, et doit être transmise à LACRIMAE. La copie textuelle brute n’est pas une couche éditoriale de rendu obligatoire.

Le principe de séparation est non négociable :

| Élément | Origine | Fonction dans la vidéo finale |
|---|---|---|
| Post réel | Champion / source sociale | Preuve visuelle affichée dans la capture PNG |
| `reaction_tweet` | PERTURABO / F04 | Commentaire original, ciblé sur le marché choisi |
| `text_emotion` | PERTURABO / F04 | Réaction courte et contextualisée affichée en motion |
| Clip mème | Release LACRIMAE | Réacteur visuel inférieur |
| `meme_tag` | Opérateur | Sélection du format ou de la famille de clip |
| `channel_id` | Opérateur | Chaîne de destination du rendu |
| Métadonnées | PERTURABO / F04 | Préparation éditoriale de la publication |

LACRIMAE ne doit ni inventer un post, ni réécrire la réaction, ni choisir le clip, ni choisir la chaîne, ni compléter une métrique manquante.

## 2. Cycle de production et responsabilités

Le flux est séquentiel. Une étape ne démarre pas tant que le Champion n’a pas validé la Gate précédente.

| Étape | Producteur | Sortie | Validation |
|---:|---|---|---|
| 0 | Champion / Oracle | Version `MEME V2`, marché, plateforme et source manuelle | Le Champion ouvre le siège |
| 1 | F01 | Source archivée, capture contrôlée, provenance et métriques | Gate 1 |
| 2 | F02 / ANGLESMITH | Angles de réaction anti-cannibalisation | Gate 2 |
| 3 | F04 | `reaction_tweet`, `text_emotion`, émotion et métadonnées par angle | Gate 3 |
| 4 | F05 | Pack assemblé hors `EXPORT`, puis pack final après validation | Gate 4 |
| 5 | LACRIMAE | Vidéo verticale finale et rapport de rendu | Publication éventuelle |

F00 est en pause pour MEME V2. F03 est ignorée : aucun clip source n’est chassé, téléchargé ou segmenté par PERTURABO. Le clip mème de production existe déjà dans la release LACRIMAE et est adressé par `clip_id` et `meme_tag`.

## 3. Structure du pack transmis

Le pack suit le schéma actif `PROFILES/logo/CONTRACTS/production_pack_schema_logo.json`. La racine conserve les champs communs du profil logo : `pack_id`, `siege_id`, `mode`, `sub_mode`, `clip_source_ref`, `angles` et `videos`. Pour MEME V2, `sub_mode` vaut obligatoirement `meme_v2` et le bloc racine `meme_v2` contient la source de production ainsi que les bindings fournis par l’Opérateur.

```json
{
  "pack_id": "LOGO-SIEGE-<siege_id>",
  "siege_id": "<siege_id>",
  "mode": "logo",
  "sub_mode": "meme_v2",
  "meme_v2": {
    "source_post": {
      "screenshot_png": "ARCHIVUM/campaign/source_<source_id>.png",
      "url": "https://source.example/post",
      "author": "@source_account",
      "observed_at": "2026-08-24T12:00:00Z",
      "metrics": {
        "likes": 0,
        "views": null,
        "comments": null,
        "reposts": null
      },
      "credit_display": "Source: @source_account"
    },
    "operator_bindings": {
      "A01": {
        "clip_id": "<clip-deja-present-dans-la-release>",
        "meme_tag": "M1",
        "channel_id": "<chaine-cible>"
      }
    }
  },
  "videos": [
    {
      "video_index": 1,
      "angle_id": "A01",
      "title": "<titre de reaction>",
      "source_post": {
        "screenshot_png": "ARCHIVUM/campaign/source_<source_id>.png"
      },
      "reaction_tweet": "<reaction originale PERTURABO>",
      "text_emotion": "My sister and me right now:",
      "emotion": "incredulous",
      "duration_sec": 8,
      "clip_id": "<clip-deja-present-dans-la-release>",
      "meme_tag": "M1",
      "channel_id": "<chaine-cible>",
      "metadata": {
        "title": "<titre>",
        "description": "<description avec attribution et contexte>",
        "tags": ["<tag valide>"],
        "hashtags": ["<hashtag valide>"]
      }
    }
  ]
}
```

Le champ `source_post.text` peut être conservé dans l’archive F01 et dans les inputs internes de PERTURABO. Il ne doit pas être injecté par LACRIMAE comme une fausse citation ou comme une seconde couche éditoriale lorsque la capture contient déjà le post. Le champ `source_post.screenshot_png` est l’asset visuel obligatoire du rendu final.

Les chemins d’assets sont relatifs à la racine convenue du pack, ou sont remplacés par une URI d’asset équivalente si l’interface LACRIMAE fonctionne par stockage distant. Un chemin inexistant, une capture vide ou une capture illisible bloque l’entrée.

## 4. Rôle précis des champs

| Champ | Traitement obligatoire par LACRIMAE | Interdiction |
|---|---|---|
| `meme_v2.source_post.screenshot_png` | Charger et afficher la capture du post au-dessus du clip | Ne pas remplacer la capture par une reconstruction inventée |
| `source_post.url` | Conserver pour traçabilité ou description lorsque disponible | Ne pas fabriquer une URL |
| `source_post.author` | Préserver l’attribution fournie | Ne pas attribuer le post à un autre compte |
| `source_post.metrics` | Utiliser uniquement comme métadonnées de provenance | Ne pas compléter une valeur `null` |
| `reaction_tweet` | Afficher le texte comme contribution PERTURABO | Ne pas le présenter comme une citation de l’auteur source |
| `text_emotion` | Afficher exactement le motion validé, avec adaptation technique minimale seulement | Ne pas changer les personnages ou réutiliser une formule d’un autre siège |
| `clip_id` | Charger le clip déjà présent dans la release LACRIMAE | Ne pas télécharger ou sélectionner un clip différent |
| `meme_tag` | Appliquer le format demandé par l’Opérateur | Ne pas le déduire ou le remplacer automatiquement |
| `channel_id` | Associer le rendu à la chaîne cible | Ne pas publier sur une autre chaîne |
| `metadata` | Transmettre titre, description, tags et hashtags validés | Ne pas ajouter une promesse de fair use ou de monétisation |

Le champ historique `tweet.text`, lorsqu’il existe encore pour compatibilité du profil logo, doit être interprété comme la **réaction affichée** produite par F04 dans le mode MEME V2, et non comme la copie brute de la source. La source réelle est toujours la capture PNG et le bloc `source_post`.

## 5. Composition visuelle imposée

Le rendu attendu est une vidéo verticale de type réaction mème. La capture du post réel est située dans la partie supérieure ; le clip mème de la release est situé dans la partie inférieure ; la réaction PERTURABO et le `text_emotion` rendent explicite la lecture humoristique ou émotionnelle proposée.

```text
┌──────────────────────────────┐
│ Capture PNG du post réel     │  ← preuve source, visible dès la première frame
│ Tweet + image déjà contenus  │
├──────────────────────────────┤
│ text_emotion contextualisé   │  ← motion court, personnes cohérentes
│                              │
│ Clip mème de la release      │  ← clip_id + meme_tag
│ Réaction / chute PERTURABO   │  ← reaction_tweet, distinct de la source
└──────────────────────────────┘
```

La capture doit être identifiable comme une capture d’un post réel. Elle ne doit pas être redessinée de façon à modifier son sens. Si le crédit est disponible, il doit rester lisible dans la capture ou être repris dans la description selon les règles de la release.

Le `reaction_tweet` est le cœur de la valeur ajoutée. Il doit rester visuellement distinct de la source, par sa position, sa hiérarchie typographique, son fond ou son traitement. LACRIMAE peut adapter la mise en page pour la lisibilité mobile, mais ne peut pas inventer une nouvelle chute ni paraphraser silencieusement le texte.

Le `text_emotion` est une courte étiquette de réaction. Il doit correspondre aux personnes, au groupe ou au contexte réellement évoqué par le `reaction_tweet`, par exemple `My sister and me right now:` ou `The neighbors watching this:`. Les formats `A:` / `B:`, les personnes absentes, les formulations génériques sans contexte et les résidus d’un ancien siège sont interdits.

## 6. Règles de durée et de mouvement

La durée vient du champ `duration_sec` du pack. Pour le format MEME V2 standard, la cible est généralement comprise entre 5 et 7 secondes ; une valeur de 8 secondes reste acceptable lorsque le pack ou la release la demande. LACRIMAE ne doit pas compresser un texte jusqu’à le rendre illisible.

| Paramètre | Règle de rendu |
|---|---|
| Ratio | 9:16 |
| Capture | Visible dès la première frame, position supérieure |
| Clip mème | Clip fourni par la release, position inférieure |
| Transition | Une bascule principale maximum, sauf instruction de release |
| Motion | `text_emotion` court, stable et lisible |
| Réaction | `reaction_tweet` séparé de la capture |
| Audio | Facultatif selon la release ; la compréhension visuelle doit rester possible |
| Watermark | Celui du pack ou de la campagne, sans en inventer un nouveau |
| Texte | Aucun texte coupé, chevauché ou illisible sur mobile |

LACRIMAE peut ajuster le timing, le recadrage et les animations techniques. Il ne peut pas modifier le sens éditorial, la relation entre les personnages, le marché ciblé ou la réaction validée.

## 7. Validation d’entrée avant rendu

Avant toute génération de vidéo, LACRIMAE doit effectuer une validation déterministe. Le traitement s’arrête avec `blocked` si une condition critique échoue.

| Contrôle | Résultat attendu |
|---|---|
| `sub_mode` | Égal à `meme_v2` |
| Capture | `screenshot_png` présent, accessible et lisible |
| Provenance | URL, auteur et date conservés lorsqu’ils ont été fournis |
| Clip | `clip_id` résolu dans la release LACRIMAE |
| Binding | Chaque angle possède `meme_tag` et `channel_id` |
| Réaction | `reaction_tweet` non vide et distinct de la source |
| Motion | `text_emotion` non vide, contextualisé et lisible |
| Métadonnées | Présentes et cohérentes avec l’angle |
| Résidus | Aucun personnage, sujet, formulation ou asset d’un autre siège |
| Format | Durée, ratio et dimensions compatibles avec la release |

LACRIMAE ne doit pas corriger automatiquement une absence de champ en devinant une valeur. Il doit retourner l’erreur, le champ concerné et le `pack_id` afin que PERTURABO ou l’Opérateur corrige la source du problème.

## 8. Pipeline de rendu recommandé

Le pipeline LACRIMAE est le suivant :

1. Lire le JSON et identifier `pack_id`, `siege_id`, `sub_mode` et les angles.
2. Résoudre `meme_v2.source_post.screenshot_png` et vérifier son hash ou son accessibilité.
3. Résoudre le binding de l’angle : `clip_id`, `meme_tag` et `channel_id`.
4. Charger le clip déjà présent dans la release ; ne pas en rechercher un autre.
5. Construire la composition verticale avec la capture en haut et le clip en bas.
6. Ajouter `text_emotion` comme motion contextualisé.
7. Ajouter `reaction_tweet` comme contribution distincte et lisible.
8. Appliquer uniquement les métadonnées et le watermark autorisés par le pack.
9. Effectuer le contrôle visuel et le contrôle de contamination entre sièges.
10. Écrire la vidéo finale et le rapport machine-readable.

La réussite technique du rendu ne vaut pas validation éditoriale. LACRIMAE ne publie pas automatiquement parce qu’un pack est techniquement `ready` : la validation du Champion et l’autorisation opérationnelle de la chaîne restent séparées du rendu.

## 9. Statuts de sortie et rapport

Pour chaque entrée ou pack, LACRIMAE doit produire un rapport déterministe similaire à celui-ci :

```json
{
  "pack_id": "LOGO-SIEGE-<siege_id>",
  "angle_id": "A01",
  "status": "ready",
  "rendered_asset": "output/A01.mp4",
  "input_sha256": "<sha256>",
  "checks": {
    "source_png_present": true,
    "source_png_readable": true,
    "source_position_upper": true,
    "clip_resolved": true,
    "reaction_present": true,
    "motion_present": true,
    "metadata_present": true,
    "source_reaction_separated": true,
    "operator_binding_complete": true,
    "foreign_siege_residue": false,
    "mobile_text_readable": true
  },
  "errors": [],
  "rendered_at": "2026-08-24T12:00:00Z"
}
```

Les statuts sont définis ainsi :

| Statut | Signification |
|---|---|
| `ready` | Le rendu respecte le contrat technique ; aucune autorisation de publication n’est implicite |
| `needs_revision` | Le contenu est présent, mais la lisibilité, le timing, le cadrage ou la séparation visuelle doit être corrigé |
| `blocked` | Une source, une capture, un clip, un binding, un texte obligatoire ou une condition de sécurité manque |

## 10. Cas de blocage obligatoires

LACRIMAE doit retourner `blocked` dans les cas suivants :

- la capture PNG est absente, inaccessible, vide ou illisible ;
- le `clip_id` n’existe pas dans la release ou ne correspond pas au binding ;
- `meme_tag` ou `channel_id` manque pour l’angle ;
- `reaction_tweet` ou `text_emotion` est absent ;
- la réaction est présentée comme une citation du compte source ;
- la capture et la réaction sont fusionnées de manière trompeuse ;
- le rendu contient un personnage, un texte, une image ou un nom provenant d’un autre siège ;
- le texte est coupé, le ratio est invalide ou la durée est incompatible ;
- une métadonnée essentielle a été inventée ou remplacée ;
- l’Opérateur demande implicitement une publication alors que le manifeste ne comporte pas la validation Champion.

En cas de défaut de formulation éditoriale ou de cannibalisation entre angles, LACRIMAE retourne `needs_revision` et renvoie la correction vers PERTURABO/F04. Le moteur de rendu ne réécrit pas le `reaction_tweet` pour résoudre un défaut stratégique.

## 11. Ordre de remise et interface de fichiers

L’interface de première version est basée sur des fichiers versionnés :

```text
PERTURABO produit les sorties F01/F02/F04
→ Champion valide Gate 1, Gate 2 et Gate 3
→ F05 assemble le pack hors EXPORT
→ Champion valide Gate 4
→ PERTURABO copie le pack dans EXPORT/
→ LACRIMAE ingère le JSON et les assets
→ LACRIMAE rend la vidéo et le rapport
→ publication éventuelle par l’Opérateur
→ F06 suit les performances
```

LACRIMAE peut consommer un `production_pack_*.json` depuis le dépôt ou depuis une URL d’asset approuvée. Le pack doit être traité comme immuable après validation Gate 4. Toute modification de source, de réaction, de motion, de tag ou de chaîne exige un nouveau contrôle par le Champion.

Une API ultérieure peut exposer une route d’ingestion et une route de statut, mais cette note ne prescrit aucune authentification, aucun stockage distant et aucun endpoint non validé par les deux projets. La remise par fichiers reste la référence d’intégration actuelle.

## 12. Critères d’acceptation

L’intégration MEME V2 est acceptée lorsque LACRIMAE peut :

1. ingérer un pack `sub_mode: "meme_v2"` ;
2. charger une capture PNG réelle et l’afficher au-dessus du clip mème ;
3. résoudre le `clip_id`, le `meme_tag` et le `channel_id` de chaque angle ;
4. afficher le `reaction_tweet` et le `text_emotion` sans les confondre avec le post source ;
5. conserver l’attribution et les métadonnées fournies ;
6. produire une vidéo verticale lisible sans inventer de contenu ;
7. bloquer proprement les packs incomplets, incohérents ou contaminés ;
8. retourner un rapport avec statut, contrôles, erreurs et empreinte d’entrée.

Le contrat est considéré comme respecté uniquement si la sortie finale permet de distinguer en un regard **la preuve source**, **la réaction PERTURABO** et **le réacteur visuel LACRIMAE**.

## 13. Références internes

- `GUIDE_UTILISATION/04_MODE_MEME.md` — workflow V1/V2 et doctrine de montage.
- `GUIDE_UTILISATION/05_NOTE_PERTURABO_PACK_MEME.md` — contrat éditorial du pack.
- `PROFILES/logo/CONTRACTS/production_pack_schema_logo.json` — schéma JSON actif.
- `PROFILES/logo/manifest.json` — manifeste du profil et référence LACRIMAE.
- `F01_SCOUT/CODEBASE/scout.py` — intake et archivage de la source manuelle.
- `F05_PACKAGER/CODEBASE/packager.py` — assemblage déterministe et export du bloc MEME V2.
- `F05_PACKAGER/CODEBASE/test_meme_v2_contract.py` — test de non-fuite de la copie textuelle et de présence des bindings.

Cette note est la référence technique de remise après validation du Champion. Elle ne remplace ni les validations de Gates de PERTURABO, ni les règles de publication propres à la chaîne cible.
