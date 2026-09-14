# 06_RECHERCHE_SUJETS_US_YOUTUBE_MEME — Guide du moteur contextualisé

> Ce guide décrit la recherche de sujets avant un nouveau siège. Il s’applique à la recherche contextualisée **YouTube Shorts**, **marché US**, **anglais** et **niche meme**, avec possibilité d’ancrer la prospection sur une chaîne, un Démon et des hashtags observés.

## 1. Rôle du moteur

F00_CAPTEURS ne choisit pas automatiquement le sujet final. Il collecte des preuves réelles, calcule un score legacy et un score contextualisé, puis remet une proposition au Champion.

Le profil de recherche est défini par cinq dimensions :

| Dimension | Valeurs initiales |
|---|---|
| Horizon | `2h`, `6h`, `12h`, `24h`, `3d`, `7d`, `30d` |
| Plateforme | `youtube_shorts` |
| Marché | `us_young_english` |
| Niche de production | `meme` |
| Décision | Validation manuelle du Champion |

Le principe est : **un sujet n’est pas seulement viral ; il doit être viral pour un horizon, une plateforme, un marché et une niche déterminés**.

## 2. Commande contextualisée

Depuis `MONDES_FORGES/CLIPPING/F00_CAPTEURS/CODEBASE/` :

```bash
python3 capteurs.py --scan-subjects \
  --niche "student debt" \
  --horizon 24h \
  --platform youtube_shorts \
  --market us_young_english \
  --niche-mode meme \
  --mode informatif \
  --n-angles 8
```

Les anciennes commandes restent valides :

```bash
python3 capteurs.py --scan-subjects \
  --niche "Lakers basketball" \
  --freshness brulant \
  --mode informatif
```

Lorsqu’une ancienne commande est utilisée, le système crée un profil de compatibilité legacy. Elle ne bénéficie pas de toute la précision du nouveau contexte, mais son fonctionnement historique est conservé.

## 3. Capteurs utilisés

YouTube constitue la preuve vidéo prioritaire. Les résultats YouTube fournissent notamment les vues, la récence, les vidéos concurrentes et les chaînes observées. Google Trends mesure la dynamique et la saisonnalité ; Google Suggest mesure les formulations recherchées ; RSS confirme la fraîcheur et la couverture ; Reddit confirme la conversation et le langage communautaire lorsque le flux est disponible.

Une source externe ne remplace jamais la preuve YouTube. Un sujet Reddit très discuté mais sans preuve vidéo suffisante est un **signal à surveiller**, pas une opportunité Shorts confirmée.

## 4. Horizons

| Horizon | Utilisation | Signal dominant |
|---|---|---|
| `2h` | Signal extrêmement récent | Accélération immédiate |
| `6h` | Sujet à exploiter immédiatement | Fraîcheur et accélération |
| `12h` | Signal qui résiste au premier cycle | Confirmation rapide |
| `24h` | Sujet encore actif après le premier pic | Équilibre fraîcheur / stabilité |
| `3d` | Sujet court terme à confirmer et décliner | Tendance récente et concurrence |
| `7d` | Sujet persistant et déclinable | Tendance et répétabilité |
| `30d` | Sujet récurrent, saisonnier ou evergreen | Demande régulière et série |

Un score obtenu pour `6h` ne doit pas être comparé directement à un score obtenu pour `30d` sans lire le profil associé.

## 5. Scores produits

Chaque candidat reçoit plusieurs dimensions :

| Champ | Signification |
|---|---|
| `score_mecanique_legacy` | Ancien score F00 conservé pour comparaison |
| `score_contextualise` | Classement contextualisé pour le profil choisi |
| `contextual_scores.us_native` | Ancrage dans une réalité américaine |
| `contextual_scores.youtube_shorts` | Preuve et adéquation vidéo YouTube |
| `contextual_scores.horizon` | Adéquation à la durée demandée |
| `contextual_scores.meme_fit` | Compression et faisabilité dans la niche meme |
| `contextual_scores.repeatability` | Capacité à produire plusieurs angles |
| `contextual_scores.confidence` | Solidité et convergence des preuves |
| `contextual_scores.reddit_confirmation` | Confirmation conversationnelle Reddit |
| `safety_gate` | `pass`, `block` ou revue Champion |
| `saturation_penalty` | Pénalité liée à la saturation observée |

Le score contextuel n’annule pas l’ancien score. Les deux doivent être examinés ensemble.

## 6. Filtre meme

Avant de livrer un sujet au siège, le Champion vérifie qu’il peut être compressé en vidéo très courte : compréhension immédiate, faux tweet de trois lignes maximum, preuve visuelle dès la première image, contraste, émotion claire, une seule bascule et plusieurs angles non cannibalisés.

Un sujet peut avoir une forte demande mais être refusé pour la niche meme s’il exige une longue explication ou ne possède aucun contraste visuel clair.

## 7. Lecture du livrable

Les fichiers sont écrits dans `F00_CAPTEURS/OUT/` puis copiés dans `EXPORT/` :

```text
subjects_proposal.json
subjects_proposal.md
```

Le Champion doit vérifier le profil, les deux scores, les preuves, les signaux manquants, la sécurité, la saturation et la compatibilité meme. Le choix du sujet reste manuel.

## 8. Inputs de référence contrôlés

Le Champion peut fournir une chaîne de référence, une vidéo de référence, un Démon ou des hashtags de niche. Les termes extraits d’une preuve sont conservés comme `observed_reference` ou `observed_demon`. Les termes générés par le Directeur premium restent `premium_proposed` jusqu’à leur vérification sur YouTube. Aucun hashtag proposé ne devient une preuve par simple génération.

Chaque candidat meme doit être confirmé par au moins une vidéo YouTube observée, avec URL, titre, chaîne, date et métriques disponibles. Trends, Suggest, Reddit et RSS servent à découvrir ou confirmer une demande ; ils ne remplacent pas la preuve vidéo.

## 9. Règles verrouillées

Le moteur n’invente jamais une métrique. Une valeur manquante reste manquante. La collecte est commanditée par le Warsmith ; aucun cron ni auto-posting n’est ajouté. Aucun sujet n’est livré à la campagne sans validation du Champion. Le scan ne télécharge pas de clip en mode meme.

La présence d’un sujet dans la proposition ne constitue pas une validation de campagne. Après le choix du Champion, le pipeline normal reprend avec les portes du siège. Oracle présente les scores et les preuves ; seul le Champion valide le sujet et la Gate.
