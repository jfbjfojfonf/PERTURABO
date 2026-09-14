# _PIEGES_APPRIS — Les leçons du siège test

> Chaque erreur listée ici a **coûté du temps en vrai** pendant le siège TS01_SANDOVAL.
> Les lire AVANT chaque siège évite de les repayer. ⏱️ 5 minutes.

---

## 1. 🗂️ Le dossier `OUT/` des frégates est GITIGNORÉ

**Le problème** : `production_pack_logo.json` vit dans `F05_PACKAGER/OUT/` → gitignoré par design (`**/OUT/*.json`). Résultat : le lien `raw.githubusercontent.com` donnait **404** et OMNIS_WATCH ne pouvait pas récupérer le pack.

**La solution** : copier le pack dans `EXPORT/` (hors OUT) et pousser :
```bash
cp F05_PACKAGER/OUT/production_pack_logo.json EXPORT/production_pack_logo.json
git add MONDES_FORGES/CLIPPING/EXPORT/ && git commit -m "export pack" && git push origin main
```
→ **Règle d'or** : *tout livrable OMNIS_WATCH passe par `EXPORT/`, jamais par `OUT/`.*

## 2. 📝 Le fair use = clause Section 107 (EN), PAS une note d'illustration

**Le problème** : la première version du pack contenait une note « videos serve purely as illustration » (ou la vieille note FR `d'illustration`). Le commanditaire exige le **paragraphe 107 officiel** (Copyright Act 1976), en **anglais US**.

**La solution** : la clause 107 complète est maintenant la valeur par défaut (`FAIR_USE_NOTE` dans `copywriter.py`). Vérification rapide :
```bash
python3 -c "import json; p=json.load(open('MONDES_FORGES/CLIPPING/F05_PACKAGER/OUT/production_pack_logo.json')); print(sum(1 for v in p['videos'] if 'Section 107' in v['metadata']['description']), '/', len(p['videos']), 'clause 107')"
```
→ Si un `< 5` : les descriptions ne sont pas conformes.

## 3. ✂️ Le résumé doit tenir en 2 LIGNES

**Le problème** : la première mouture des descriptions avait un résumé en 1 paragraphe long. La spec exige un **paragraphe de résumé en 2 lignes** en tête de description, puis le paragraphe fair use.

**La leçon** : à la gate 3, on montre le texte RÉEL (pas un « résumé de résumé ») et le résumé doit être court et factuel.

## 4. 🔑 La clé premium n'arrive pas toujours dans le sandbox

**Le problème** : `CLIPPING_PREMIUM_API_KEY` (API Keys) n'était pas lue par F04 pendant le test → `--generate` plantait (« Clé premium absente »).

**La solution** : le mode backup `--oracle` :
```bash
python3 copywriter.py --generate --angle A01 --oracle
```
→ F04 écrit le prompt dans `F04_COPYWRITER/IN/premium_call_A01.json`, l'Oracle forge `OUT/text_payload_raw_A01.json`, on relance, ça passe. **Même pipeline, même validation, juste une source de génération différente.**

## 5. 🚪 Le vocabulaire « porte » vs « gate »

**Le problème** : le ledger utilise `porte` (liber_clipping.json → `portes_validated`, `current_porte`), mais tout le monde dit **gate** en conversation.

**La leçon** : les deux désignent la même chose. `current_porte: p4` = la gate 4 est la prochaine. Ne pas s'étonner en lisant le ledger.

## 6. 🧵 Le `--start-siege` écrase la configuration du mode logo

**Le problème** : re-lancer `--start-siege` peut réinitialiser/écraser l'état du siège en cours (mode logo → défaut).

**La leçon** : ne JAMAIS relancer `--start-siege` en cours de siège. Vérifier l'état avec `--status` avant. Si le siège a tourné par erreur, les logs de `TRACKING/CLIPPING_LOG.md` montrent la trace.

## 7. 📝 Remplacer du texte dans un JSON = RISQUE DE CORRUPTION

**Le problème** : lors du remplacement de la clause fair use par `str_replace` sur les `text_payload_*.json`, un fichier s'est retrouvé **corrompu** (JSON invalide → le pack ne se régénérait pas).

**La leçon** : après toute édition manuelle d'un JSON, **toujours valider** :
```bash
python3 -c "import json; [json.load(open(f'MONDES_FORGES/CLIPPING/F04_COPYWRITER/OUT/text_payload_{a}.json')) for a in ['A01','A02','A03','A04','A05']]; print('JSON OK')"
```

## 8. 🏗️ En mode logo, F03 est SKIPPÉ

**Le problème** : les « Artefact introuvable » affichés lors des validations de gate sont normaux en mode logo — le pipeline attend des artefacts de F03 qui n'existe pas dans ce mode.

**La leçon** : en mode logo, le flux est F01 → F02 (verdict + angles) → F04 (textes) → F05 (pack). Pas de F03. Ce n'est pas une erreur.

---

## 🧭 Comment utiliser ces leçons

- Avant chaque siège : relire cette page.
- Si tu rencontres une erreur **pas encore listée** : la noter ici (et dans `TRACKING/CLIPPING_LOG.md`) pour le prochain champion.

## 9. Le Directeur premium ne remplace pas les preuves

Le premium peut diriger l’interrogation, mais il ne remplace pas les capteurs. Il formule les hypothèses, questions et requêtes ; l’Oracle collecte les réponses et conserve les URLs, dates et métriques. Une question premium n’est jamais une preuve.

Ne jamais laisser le premium remplir un quota de candidats, inventer une URL, compléter une métrique absente, transformer un désert en océan bleu ou présenter une interprétation comme une observation. Si la clé est absente, le fallback déterministe doit rester explicite.

## 10. La boucle adaptative est limitée

Le Directeur dispose de trois tours maximum. Un tour supplémentaire doit répondre à une lacune identifiée : preuve YouTube absente, Démon incomplet, contradiction, doublon ou hypothèse d’océan bleu non vérifiée. Une collecte qui n’améliore plus la preuve doit s’arrêter.

## 11. Faits et interprétations restent séparés

Les réponses brutes de l’Oracle et les analyses du Directeur doivent rester dans des blocs séparés. Avant validation Champion, vérifier `invented = 0`, les URLs autorisées, les sources, le statut de confiance et l’état `warsmith_review`.

## 12. Leçons du siège New York Bagel — mode MEME

- **Le Champion est l’unique autorité des Gates.** Oracle présente, contrôle et suggère ; Oracle ne valide ni ne rejette à la place du Champion.
- **Un siège fermé ne doit pas contaminer le suivant.** Après export et décision du Champion, exécuter `IW_CUSTOS.py --mode close-campaign` et ne pas réutiliser automatiquement ses inputs.
- **Le tweet et le texte motion sont deux champs distincts.** Le tweet raconte le gag ; `text_emotion` est la réaction centrale, en quatre mots maximum, terminée par `:` et cohérente avec les personnes réellement présentes.
- **Aucun résidu d’un ancien siège.** Les textes motion ne doivent jamais conserver un personnage, une formule ou un sujet d’un autre siège.
- **Anti-cannibalisation de forme.** Dix tweets ne doivent pas recycler la même mécanique. Varier relation, lieu, déclencheur, réaction et chute ; contrôler les doublons sémantiques et structurels.
- **F05 n’écrit rien.** Il assemble les payloads F04, la balise mème et les métadonnées. Le mode logo/meme produit un pack unique `production_pack_logo.json` avec `videos[]`.
- **La balise mème doit être explicite.** Une balise comme `M1` peut être commune aux dix vidéos si le Champion l’a décidée ; elle ne doit pas être confondue avec les anciens identifiants `meme_001` / `meme_002`.
- **Revue avant export.** F05 peut assembler hors `EXPORT`, mais la copie dans `EXPORT/` et l’expédition à LACRIMAE attendent la validation explicite du Champion.


## 13. MEME V2 — source sociale et réaction puissante

Le mode MEME V2 commence par une source sociale réelle fournie par le Champion : copie textuelle, capture, URL, auteur, date et métriques disponibles. F00 est en pause ; F01 archive et contrôle la provenance. Une source sans preuve ou sans contexte exploitable reste en revue et ne doit pas alimenter une série.

Le `reaction_tweet` est la pièce stratégique principale. Il doit viser le marché déclaré, apporter un point de vue ou une chute et être clairement distinct de la source. Dix mini-scènes inventées autour d’un mot-clé, ou dix reformulations d’un même gag, ne constituent pas une stratégie meme viable.

Le `text_emotion` est produit après la réaction et reste simple : il correspond aux personnes ou à l’audience du contexte (`Young adults seeing this:`, `My sister and me right now:`). Les résidus d’un autre siège, les marqueurs `A:` / `B:` et les motions génériques sont des erreurs bloquantes.

F05 assemble la source, la capture, le crédit, la réaction et les métadonnées ; il ne génère rien. Le Champion valide chaque Gate, l’Oracle suggère uniquement, et l’export ainsi que la fermeture restent postérieurs à cette validation.

En V2, la copie textuelle du tweet reste interne à F01, tandis que la capture PNG — qui contient le tweet et son image — est obligatoire dans le pack final. LACRIMAE l’affiche au-dessus du clip mème de sa release. `clip_id`, `meme_tag` et `channel_id` doivent être fournis par l’Opérateur ; leur absence bloque le finalizer.
