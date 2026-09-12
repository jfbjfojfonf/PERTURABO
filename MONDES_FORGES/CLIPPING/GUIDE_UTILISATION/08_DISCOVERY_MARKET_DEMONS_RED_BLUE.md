# 08_DISCOVERY_MARKET_DEMONS_RED_BLUE — Découverte stratégique

## Principe

Ce mode permet au Champion de fournir uniquement un **marché**, une **plateforme** et un **horizon**. F00_CAPTEURS recherche alors les candidats à partir de preuves observées. Il ne reçoit pas un mot-clé imposé et n’invente jamais de candidats pour remplir un quota.

## Commande

Depuis `MONDES_FORGES/CLIPPING/F00_CAPTEURS/CODEBASE/` :

```bash
python3 capteurs.py --discover-market \
  --market "US residents age 25-45 interested in @Zdak" \
  --platform youtube_shorts \
  --discovery-horizon 3d
```

Pour demander dix angles après la sélection :

```bash
python3 capteurs.py --discover-market \
  --market "US residents age 25-45 interested in @Zdak" \
  --platform youtube_shorts \
  --discovery-horizon 3d \
  --discovery-angles 10 \
  --blue-angles 6 \
  --red-angles 4
```

Le système écrit `OUT/market_discovery_proposal.json`, `OUT/market_discovery_proposal.md` et les copies dans `EXPORT/`. Aucun siège n’est lancé automatiquement.

## Démons

Un Démon est un créateur, une chaîne ou un pattern dominant observé dans le territoire de la cible. Le système conserve son identité, ses titres observés, ses vues, ses URLs, sa pression et son statut. Un Démon n’est pas automatiquement un ennemi : il peut révéler une demande, une saturation ou une faille exploitable.

## Candidats et océans

Le système tente de produire jusqu’à 30 candidats réellement observés. Il ne complète pas artificiellement le quota.

| Camp | Définition |
|---|---|
| Océan rouge | Demande et preuve vidéo fortes, avec pression concurrentielle observée |
| Océan bleu | Demande suffisante, espace moins saturé et hypothèse vérifiable |
| Désert | Faible concurrence sans demande prouvée ; non classé comme bleu |

La répartition 15/15 est une cible d’analyse, pas une obligation. Les horizons disponibles sont `2h`, `6h`, `12h`, `24h`, `3d`, `7d` et `30d`. Une sortie peut contenir moins de 30 candidats ou moins de 15 bleus si les preuves ne suffisent pas.

## Anti-invention et anti-doublons

Les requêtes dérivées du marché sont seulement des sondes. Un candidat doit posséder `observed: true` et des `evidence_urls`. Les candidats similaires sont regroupés par clé normalisée ; le meilleur représentant est conservé et les autres sont enregistrés comme doublons.

Le Champion doit examiner le nombre de candidats inventés, qui doit toujours être égal à zéro, le nombre de doublons supprimés et les preuves de chaque candidat.

## Packs et angles

Les packs de deux candidats sont proposés seulement après le classement. Ils utilisent une ancre de demande et un contraste distinct. L’allocation d’angles est indépendante de la répartition initiale : `6 bleu + 4 rouge` est possible si les deux camps ont assez de candidats disponibles. Sinon, le système retourne `insufficient_candidates` et demande une décision du Champion.

## Validation

L’état de sortie est `warsmith_review`. Le Champion peut valider des candidats, rejeter des doublons, demander des remplacements ou refuser toute la liste. La validation ne doit être suivie d’une production qu’après lecture des preuves, des Démons, du camp et du niveau de confiance.


## Barrières de production meme

Pour `production_niche=meme`, un résultat Trends, Suggest, Reddit ou RSS est une piste, pas un candidat. Le candidat doit être confirmé par au moins une vidéo YouTube observée, présenter un signal meme identifiable, être pertinent pour le Démon ou le marché cible, rester compatible avec Shorts et franchir le contrôle de sécurité. Un résultat informatif, sportif, immobilier, musical ou généraliste est rejeté s'il ne possède pas de preuve de format meme dans l'écosystème ciblé.

Les candidats sans preuve YouTube, sans pertinence cible, sans signal meme ou avec une confiance insuffisante sont conservés dans `rejected_signals`, `observation_only` ou `desert`. Ils ne remplissent jamais le quota de 30.

## Chaînes et hashtags comme inputs contrôlés

Une chaîne de référence et les Démons peuvent fournir des inputs explicites :

```bash
python3 capteurs.py --discover-market \
  --market "US audience 25-45 fans of target creator" \
  --platform youtube_shorts \
  --discovery-horizon 3d \
  --reference-channel "@reference_creator" \
  --reference-hashtag "#observed_tag" \
  --demon-hashtag "#demon_tag"
```

Les hashtags extraits d'une chaîne ou d'un Démon sont des termes observés. Les hashtags proposés par le Directeur premium sont des sondes et doivent être vérifiés sur YouTube avant de servir au classement. Chaque terme doit conserver sa provenance : `observed_reference`, `observed_demon`, `derived_query`, `premium_proposed` ou `unverified`.

## Anti-cannibalisation

La déduplication compare le vocabulaire, le sens, le hashtag, le territoire, le hook, l'émotion, le format et l'historique. Deux candidats qui produisent le même Short sont cannibalisants même si leurs mots diffèrent. Un pack à deux mots doit utiliser une ancre de demande et un contraste réel ; une combinaison redondante est refusée.

## Directeur premium

Baseten peut être configuré comme provider OpenAI-compatible avec `https://inference.baseten.co/v1`. Le Directeur propose les questions et requêtes ; F00 collecte les réponses réelles ; le garde-fou vérifie les URLs et métriques. Le premium ne peut pas fabriquer une preuve et ne peut pas transformer une hypothèse en fait.
