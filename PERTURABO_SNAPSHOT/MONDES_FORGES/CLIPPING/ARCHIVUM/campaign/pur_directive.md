# Directive — Mode PUR (Clipping Pur)
Campaign ID: PUR_SIEGE_DEFAULT
> MODE PUR: extraction de moments viraux depuis un podcast/long-form.
> Le Warsmith fournit le podcast (transcript.json + vidéo) + le style (ranking/reframing/blur/split_scene).
---

## Marché du siège
- **Marché** : À DÉFINIR par le Warsmith
- **Plateforme** : YouTube Shorts / TikTok / Instagram Reels
- **Langue / région** : À DÉFINIR par le Warsmith
- **Sous-mode** : pur
- **Style** : ranking | blur | split_scene | reframing (À CHOISIR)
- **Nombre de clips** : 1 à 10 (selon le style)
- **Durée clip** : 15-60 secondes (optimal 30-45s)

## Règles stratégiques
- **Strict-source** : uniquement les assets fournis (transcript.json + vidéo source)
- **Hook** : 0-3 secondes MAX — visage speaker, pas de B-roll
- **Captions** = transcript du speech (pas de texte écrit)
- **Pas de CTA** : contenu organique (pas "abonne-toi", "like", "partage")
- **Anti-detection** : obligatoire (1 traitement visuel + 1 audio par clip)
- **Langue** : choisie par le Warsmith (FR ou EN)
- **Oracle** : génère les titres via clé premium + ARCHIVUM
- **Warsmith** : valide les titres et labels

## Style-specific
### Ranking
- **Titre principal** : MAX 4 MOTS
- **Label clip** : 1 MOT (2 si article)
- **Clips** : 1 à 6 maximum
- **Countdown** : #1 = plus captivant, dernier = meilleur moment

### Blur
- **Titre principal** : ~2 LIGNES (pas de limite de mots stricte)
- **Label clip** : AUCUN
- **Clips** : 1 à 10

### Split Scene
- **Titre principal** : ~2 LIGNES, positionné AU CENTRE
- **Label clip** : AUCUN
- **Clips** : 1 à 10
- **Sous-layouts** : A_image_ia / B_video_broll / C_2_speakers / D_preuve

### Reframing
- **Titre principal** : ~2 LIGNES
- **Label clip** : AUCUN
- **Clips** : 1 à 10
- **Principe** : le titre TRANSFORME le sens (pas une description)

## Exclusions
- ❌ CTA ("abonne-toi", "like", "partage")
- ❌ Clickbait sans payoff
- ❌ Source non-issue du transcript
- ❌ Clip non-transformative (anti-doublon avec source)
- ❌ Sujets politiques, religieux, controversés, violents
- ❌ B-roll sur le moment émotionnel le plus intense
- ❌ Phrases captions trop longues
- ❌ Silences > 3 secondes

## Anti-detection (obligatoire pour tous les styles)
- **Mirror** : obligatoire (ranking, split_scene) / optionnel (blur, reframing)
- **Speed** : 1.05x
- **Zoom** : Punch 110-115% (ranking, split_scene) / Breathing 105-110% (blur) / Slow push 102-108% (reframing)
- **SFX** : 5-6 par clip (ranking, split_scene) / 1-2 par clip (blur, reframing)
- **Crop** : 2-3%

*Fer au-dedans, Fer au-dehors. Le siège continue.* 🔩