# F00D_NARRATIVUM — La Sous-frégate Compositeur (Caviar 99 %)

> **Mission unique** : prendre un clip basique validé (gate GO de F00B/F00C)
> et émettre le `caviar_manifest.json` qui transforme le rendu standard du
> bras armé (LACRIMAE) en montage narratif.
> « Le compositeur est aveugle : il ne voit ni les assets, ni le rendu —
> il lit le signal, écrit la partition, refuse la surcharge. »

Statut : ACTIVÉE (Warsmith, 2026-09-13). Sœur de F00A/F00B/F00C — appelée
par F00C (banc d'essai, YouTube) puis F00B (portage, Twitch).

---

## 1. Le contrat en une phrase

**Entrée** : un candidat validé (run_id, timestamps, score, heatmap locale)
+ le média du segment.
**Sortie** : `caviar_manifest.json` (schéma `caviar.v1`) — partition complète
et autoportante que le bras armé exécute au pixel et à la milliseconde.
**Jamais** : la frégate ne rend, ne touche au speed (décision opérateur 1.05),
au cadre 9:16, aux gates LACRIMAE, ni aux assets.

## 2. Les trois styles (matière F00C → recette F00D)

Chaque style change le placement des événements. **Constante transversale** :
le flash blanc et le B-roll RACCOURCISSENT le pacing local (le plan qui les
porte se termine plus tôt) et **l'audio du streamer est toujours maintenu**
sous les effets — jamais de mute sauf smash cut audio au climax (ducking).

### Style SPLIT (webcam + jeu, split-screen classique)
- **Où** : les moments webcam (réactions) portent les punch-ins ; le jeu porte les B-rolls.
- **Recette** : punch-in sur la webcam aux pics d'amplitude ; le trio
  B-roll+flash+SFX s'installe sur la MOITIÉ JEU (l'action continue sur la
  webcam) ; le pacing local se raccourcit autour du trio (le plan de jeu
  s'achève plus tôt, retour rapide sur la webcam = la réaction).
- **Audio** : voix + son de jeu maintenus ; SFX uniquement à l'entrée du trio.

### Style REFRAMING (9:16, l'enjeu fictif posé frame 0)
- **Où** : l'overlay d'accroche (texte, écrit par PERTURABO/l'opérateur)
  occupe le tiers supérieur de la frame 0 jusqu'au climax (rupture).
- **Recette** : in media res (l'intro est coupée) ; le regard reste centré
  (recadrage dynamique si coordonnées dispo) ; B-roll qui ILLUSTRE l'enjeu
  du reframe ; flash d'entrée + SFX ; au climax → ducking + flash autorisé ;
  après `resolution_at` → pacing lent, RIEN ne s'ajoute.
- **Audio** : voix maintenue en permanence sauf ducking au climax.

### Style RANKING (top 5 / top 10, structure décomptée)
- **Où** : chaque item du classement = une cellule narrative
  (montée → pic → retombée courte).
- **Recette** : le trio B-roll+flash+SFX marque l'ENTRÉE de chaque item ;
  pacing serré dans la montée (cuts < 2 s), court relâchement au pic ;
  punch-in sur la révélation du rang ; l'item #1 a droit à un budget majoré
  (un smash audio en plus).
- **Audio** : voix maintenue ; SFX à l'entrée d'item uniquement ; un silence
  de 0,3-0,5 s autorisé juste avant la révélation du #1.

### Style BLUR (panneau flouté, l'écran se libère pour le message)
- **Où** : le flux source n'est PAS masqué par un asset — il est crop-zoomé
  (×1.3) puis flouté (rayon ~18 px) derrière un panneau vertical de texte.
- **Recette** : le trio devient **blur+flash+SFX** (inséparable, même budget
  broll_trio) ; hook in medias res `climax_first` comme reframing ; l'overlay
  d'accroche occupe le panneau jusqu'au climax (rupture) ; punch-ins sur pics
  d'amplitude ; RIEN après la résolution.
- **Audio** : voix du streamer MAINTENUE sous les effets ; SFX uniquement à
  l'entrée du panneau blur ; smash audio au climax (ducking −12 dB).

## 3. Le Budget d'Attention (transmis au bras armé)

Source de vérité unique : `caviar_budget.json` (versionné dans CODEBASE/).
Clip de 30 s = **100 unités**, dépense max **≤ 55** (le reste = respiration) :

| Événement | Coût | Cap dur |
|---|---|---|
| Trio B-roll+flash+SFX | 12 u | ≤ 3/clip, ≤ 45 frames chacun, jamais pendant la résolution |
| Smash audio (climax) | 8 u | ≤ 2 |
| Punch-in | 6 u | ≤ 4, espacés ≥ 2 s |
| Jump cut (trim silence) | 1 u | ≤ 8 (sinon segment déclaré mauvais) |

Dépassement → **la frégate refuse d'émettre** (pas de manifeste toxique) et
renvoie un diagnostic. Double barrage : les gates P-CAV du bras armé
revérifient au rendu (mêmes constantes, même fichier). Troisième barrage :
la validation opérateur dans la War Room.

**Règle de l'élément unique** : jamais 2 événements visuels forts sur la même
frame. **SFX uniquement** à l'entrée d'un B-roll (le seul SFX du clip).
Pas de B-roll possible (pas d'assets) → pas de SFX.

## 4. Bibliothèque B-roll numérotée (hébergée chez le bras armé)

- Assets physiques chez LACRIMAE, numérotés `B-01`, `B-02`, …
- La frégate ne connaît que l'**index sémantique** (numéro → émotion →
  durée max), jamais les fichiers (zone grise de droits, repo léger).
- La frégate émet : `{ "broll_id": "B-01", "start_sec": 8.5,
  "duration_frames": 36, "entry_flash": true, "sfx": "impact" }` —
  position/durée/emballage décidés par la frégate, fichier résolu par le bras.
- Remplacer un asset = zéro modification de manifeste.

## 5. L'Archivum (règle : pas d'Archivum dans l'Archivum)

La mémoire de la frégate vit dans l'Archivum global de la flotte :
`ARCHIVUM/montage/narrativum/`
- `manifest_ledger/` — chaque manifeste émis, lié à son run (rejouabilité).
- `gate_history.json` — verdicts opérateur + raisons (la frégate apprend les goûts).
- `retention_log.json` — A/B caviar vs basique (vues, rétention). Sans mesure,
  pas de preuve — la Phase 4 (portage F00B) exige des chiffres.
- `lessons.json` — pièges appris, format court.

Lecture : toute la doctrine flotte (lecture seule, sens unique).
Écriture : uniquement dans `narrativum/`.

### 5bis. Sources d'autorité (la frégate hérite de la sagesse de la flotte)

La frégate ne réinvente rien : elle charge en CONTRAINTES les règles déjà
actées de l'Archivum du CLIPPING (`MONDES_FORGES/CLIPPING/ARCHIVUM/montage/`) :

| Fichier (patterns/) | Ce que la frégate en tire |
|---|---|
| `style_split_scene.json` | layout split : clip en haut, hook au centre, contenu bas |
| `style_ranking.json` | structure top N, caps b-roll par durée, stratégie d'items |
| `style_reframing_916.json` (+ racine ARCHIVUM/montage/patterns/reframing_916.json) | reframe 9:16, hook non-broll, placement sujet |
| `broll_integration.json` | scoring intelligent, hook jamais b-roll, caps par durée |
| `cut_patterns.json` · `energy_patterns.json` · `zoom_patterns.json` · `audio_presets.json` | grammaire des cuts, courbes d'énergie, presets son |
| `hooks_psychology.json` · `text_overlay_patterns.json` | psychologie d'accroche, styles d'overlay |

Sources narratives (transcripts/ — socle de la chimie, récolte Warsmith) :
`J0ydlAqg6_8_tim_runia.json` (7 cuts), `dhpazqW_OaU_tim_runia.json`
(5 secrets storytelling), `oiNnWm8Z5l4_tim_runia.json` (21 erreurs fatales),
`7_cuts_session_warsmith.json` (vocabulaire contractuel).

En cas de conflit entre un pattern et `caviar_budget.json`, le budget gagne
(il est plus récent et plus strict) — et le conflit est consigné dans
`lessons.json`.

## 6. Piles techniques (CPU only — si un besoin exige un GPU, on sur-conçoit)

`ffmpeg silencedetect` · `numpy` sur WAV (amplitudes — muscle F00C) ·
`faster-whisper` CPU sur le segment 30 s (mots, punchline, timing overlay) ·
heatmap F00C réutilisée · sortie `caviar.v1` · exécution dans le sillage du
workflow F00C.

**Référentiel temporel** : tout `caviar.v1` est exprimé en **secondes
relatives au segment** (jamais à la source) — le bug d'offset est interdit
par le schéma.

## 7. Phases (chaque étape = commit + patch kit + push kbkjhjhl)

- **Phase 0** — cette doctrine + scaffold Archivum + `caviar_budget.json` + docs.
- **Phase 1** — `caviar_director.py` : silences, amplitudes, budget, émission
  `caviar.v1` + tests hors-ligne verts.
- **Phase 2** — premier manifeste réel sur un candidat Sophie Rain (gate
  opérateur au préalable) + affichage lisible War Room.
- **Phase 3** — option `--to-caviar` workflow F00C + docs (guide 19+, logs) + miroir.
- **Phase 4** (après preuve de rétention) — portage F00B.

## 8. Ce que la frégate n'est PAS

Pas un moteur de rendu · pas un gate · pas un décideur final ·
pas un générateur d'accroches automatiques (elle propose des candidates,
l'opérateur tranche — l'analyse dit OÙ est la tension, pas QUOI écrire).
