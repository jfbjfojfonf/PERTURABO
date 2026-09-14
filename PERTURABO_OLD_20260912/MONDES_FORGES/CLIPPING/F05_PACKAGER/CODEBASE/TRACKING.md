# F05_PACKAGER — TRACKING.md

> *"Le fer est forgé. Les angles sont tracés. La pièce finale est prête pour l'usine. Le ferrier emballe."*
> *Frégate d'assemblage final. Lancier de la Porte 4 — expédie les N packs à LACRIMAE.*

---

## RÔLE

F05_PACKAGER est la **frégate finale de la Porte 4**. Elle assemble tous les artefacts produits par F01 → F04 et forge les N `production_pack.json` qui seront consommés par LACRIMAE.

Un pack = 1 vidéo pour 1 plateforme pour 1 marché. Pour N angles, on a N packs.

---

## INPUTS

| Input | Source | Format | Obligatoire |
|---|---|---|---|
| `angles.json` | ANGLESMITH | JSON | ✅ |
| `source_specimen_<angle>.json` (N) | F03_SOURCE_HUNTER | JSON N | ✅ |
| `text_payload_<angle>.json` (N) | F04_COPYWRITER | JSON N | ✅ |
| `verdict.json` | F02_TYRANT_CAMP | JSON | ✅ |
| `reference_skeleton.json` (style extrait) | F01_SCOUT/F04 → `reference_style` | JSON | ✅ |
| `platform_target` | Warsmith (input 3) | string | ✅ |
| `market_target` | Warsmith (input 4) | string | ✅ |

---

## OUTPUTS

### `OUT/production_pack_<angle_id>.json` (N packs)

Voir `CONTRACTS/production_pack_schema.json` pour le schéma JSON canonique (contrat interface LACRIMAE). Le pack contient les 9 blocs :

1. `IDENTITÉ` — campaign_id, angle_id, pack_index/total
2. `CIBLES` — target_platform, target_market
3. `SOURCE` — url de l'asset, suggested_segments, source_segment_sec (assets uniquement — hérésie sinon)
4. `ANGLE` — family, emotion, engagement, reframe, hook_style_fit, loop_tech, anti_cannibal_diff, blue_ocean
5. `CUT` — clip_max/min_duration, moments_to_chase, moments_to_avoid, forbidden
6. `STYLE` — pacing, energy_level, cut_density, color_palette, text_treatment (ADN observé du clip de référence — matière première brute, LACRIMAE applique ses presets coloring en plus)
7. `TEXT_PAYLOAD` — 3 titres + paragraphe (3 vetos) + caption + hashtags + on-screen + cta
8. `COMPLIANCE` — disclosure "#ad", submit_deadline_min=60, source_permission="campaign_provided"
9. `METADATA` — title_pattern, description_skeleton
+ `SUBMISSION_CHECKLIST` (active, imbriquée)

### Autres
- `OUT/packager_summary.md` — synthèse lisible Warsmith : "N packs prêts à expédier → LACRIMAE"
- `OUT/packs_index.json` — index des N packs pour LACRIMAE

---

## SUBMISSION CHECKLIST (imbriquée dans chaque pack)

Active, pas passive. À chaque pack, F05 génère une checklist que F06_TRACKER activera après Porte 4 :

```json
"submission_checklist": {
  "items": [
    {"id": "post_on_platform", "label": "Poster sur {target_platform}", "status": "pending"},
    {"id": "submit_whop_under_1h", "label": "Soumettre Whop dans l'heure", "deadline_min": 60, "status": "pending"},
    {"id": "log_link_c06", "label": "Logger le lien dans F06_TRACKER", "status": "pending"},
    {"id": "view_check_1h", "label": "Relever vues à 1h", "status": "pending"},
    {"id": "view_check_24h", "label": "Relever vues à 24h", "status": "pending"},
    {"id": "payout_flag_low", "label": "Flag si payout < seuil", "status": "pending"},
    {"id": "feedback_learnings", "label": "Nourrir learnings.json", "status": "pending"}
  ]
}
```

---

## PATTERN D'EXÉCUTION

```
python packager.py --assemble --angles ../F02/OUT/angles.json
# Pour chaque angle :
#   1. Lit source_specimen_<angle>.json
#   2. Lit text_payload_<angle>.json
#   3. Lit verdict.json (pour blue_ocean, reference_skeleton)
#   4. Lit reference_style (depuis F01 ou F04)
#   5. Assemble en production_pack_<angle>.json
#   6. Génère submission_checklist imbriquée

python packager.py --finalize
# Check-in IW_CUSTOS + packs_index.json
```

F05 ne fait **pas** appel à l'IRON — c'est un enchaînement purement déterministe d'assemblage JSON. Pas de "préparation de prompt". La tâche est mécanique : fusion de JSONs.

---

## CONTRATS RÉFÉRENCÉS

- `CONTRACTS/production_pack_schema.json` — schéma canonique (contrat avec LACRIMAE)
- `ARCHIVUM/platform_generator/{plateforme}_profile.md` — pour clip_max_duration, clip_min_duration
- `ARCHIVUM/rules/clipping_rules.md` — pour forbidden[], source_permission

---

## DÉPENDANCES

- **Amont** : tous (F01-F04 + verdict)
- **Downstream** : 
  - LACRIMAE (consomme les N packs via mode `--pack production_pack.json`)
  - F06_TRACKER (lit `submission_checklist` imbriquée, l'active après Porte 4)

---

## HÉRÉSIES

- ❌ Inclure un asset non-F03 dans `SOURCE`
- ❌ Inclure un texte non-F04 dans `TEXT_PAYLOAD`
- ❌ Omettre `reference_style` (matière première brute à transmettre à LACRIMAE)
- ❌ `source_permission` != `"campaign_provided"` = hérésie
- ❌ Inclure des hashtag/caption non validés par F04 → F05 ne forge rien, il assemble

---

## STATUT

| Phase | État | Notes |
|---|---|---|
| Arborescence créée | ✅ | |
| TRACKING.md rédigé | ✅ | Ce fichier |
| Code Python implémenté | ✅ | v1 — commit bdd7013 (tests mock TEST_F05) |
| `packager.py` | ✅ | `--assemble` (N packs) + `--finalize` (validation + packs_index + summary + check-in IW_CUSTOS F05) |
| `libs/schema_validator.py` | ✅ | Validateur draft-07 maison fidèle au schéma canonique (type/required/enum/const/min-maxItems/contains) |
| `libs/reference_style_extractor.py` | ✅ | ADN style : `reference_style.json` campagne → bloc du reference_clip.json → défauts `observed: false` + prompt vision IRON |
| `requirements_c05.txt` | ✅ | stdlib pure (jsonschema optionnel documenté) |

### Décisions v1 (résumé)
- F05 ne forge rien, il assemble : text_payload/blocs strictement copiés depuis F04, video_url strictement dans les assets F01 (règle C1) — hérésies refusées à `--assemble` comme à `--finalize`.
- `blue_ocean` sans null : depth/territory/rationale émis uniquement pour les angles réellement océan bleu (schéma canonique intact, pas de coordination LACRIMAE nécessaire).
- `forbidden` contient obligatoirement `silences > 3s` (contrainte `contains` du schéma).
- `reference_style.observed` (bool, champ additionnel) : distingue ADN réel de l'ADN par défaut — la `note` reste la const figée du contrat.
- Fourchettes cut : profil `ARCHIVUM/platform_generator/{p}_profile.md` (regex `clip_min/max_duration`), défauts déclarés sinon — aligné sur F03 duration_guard.

*Fer au-dedans, Fer au-dehors.*

## Addendum MEME — pack logo actuel

En mode `logo` / `meme`, F05 produit un pack unique `OUT/production_pack_logo.json` contenant `videos[]`, et non un fichier séparé par angle. F01 et F03 sont ignorés : le pack consomme les angles F02 et les payloads F04 du mode meme. Quand aucun payload F04 finalisé n’existe encore, le fallback contrôlé lit `text_payload_raw_Axx.json` après revue du Champion ; F05 ne forge ni texte ni métadonnée.

Chaque vidéo doit conserver `tweet.text`, `text_emotion`, `emotion`, les métadonnées et une balise mème validée par le Champion. Une même balise, telle que `M1`, peut être appliquée aux dix vidéos si le Champion le décide. Le texte motion doit rester cohérent avec les personnes du tweet et ne doit jamais provenir d’un ancien siège.

L’assemblage F05 est distinct de la validation et de l’export. Le Champion examine le pack complet avant la copie dans `EXPORT/`. F05 ne clôture pas le siège et ne décide jamais à la place du Champion. La clé premium est utilisée par F04 lorsque la génération éditoriale l’exige ; F05 reste déterministe.


## Addendum MEME V2 — source sociale et transformation

En mode MEME V2, F05 assemble un pack à partir de `source_post` fourni et contrôlé par F01 et des sorties F04. Le pack doit conserver séparément la copie du post original, sa capture, son URL, son auteur, sa date et ses métriques, puis la contribution PERTURABO : `reaction_angle`, `reaction_tweet`, `text_emotion` et `metadata`.

F05 ne réécrit aucun de ces champs et ne sollicite pas de modèle premium. La capture et le crédit de la source sont destinés à LACRIMAE ; la réaction originale doit être visuellement distinguée de la source. Les angles et les réactions déjà validés par le Champion ne peuvent pas être remplacés par une paraphrase automatique.

Une balise mème, comme `M1`, peut être commune à plusieurs vidéos uniquement si le Champion l’a explicitement choisie. L’export dans `EXPORT/`, l’expédition et la fermeture du siège restent des étapes séparées, postérieures à la revue et à la validation explicite du Champion.


## Addendum MEME V2 — contrat corrigé de sortie

En MEME V2, F05 assemble un pack unique `OUT/production_pack_logo.json` destiné à LACRIMAE. La copie textuelle du tweet fournie par le Champion reste une donnée d’analyse interne archivée par F01 ; elle n’est pas une couche textuelle obligatoire du pack final.

La **capture PNG** du tweet est en revanche obligatoire dans le pack final : elle contient déjà le tweet et son image et sera affichée au-dessus du clip mème par LACRIMAE. Le clip mème de base est référencé par `clip_id` et `meme_tag`. Le `channel_id` et le `meme_tag` sont fournis par l’Opérateur pour chaque angle.

Chaque entrée MEME V2 doit contenir `source_post.screenshot_png`, `reaction_tweet`, `text_emotion`, `metadata`, `clip_id`, `meme_tag` et `channel_id`. F05 ne génère pas la vidéo, ne réécrit pas la réaction et ne choisit ni le tag ni la chaîne. Il assemble ; LACRIMAE réalise le rendu final avec la capture en haut et le clip mème en bas.

Le finalizer MEME V2 bloque si la capture PNG, le clip, le tag ou la chaîne manque. L’export et la fermeture restent postérieurs à la revue explicite du Champion.
