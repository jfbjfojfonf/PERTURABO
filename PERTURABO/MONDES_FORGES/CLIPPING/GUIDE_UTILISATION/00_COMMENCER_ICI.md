# 00_COMMENCER_ICI — Le strict minimum pour lancer un siège

> À lire en premier. Après ça, ouvre le guide de ton mode (`01_MODE_LOGO_INFORMATIF.md` par défaut).
> ⏱️ Temps de lecture : 5 minutes.

---

## 1. Les 3 choses à savoir avant tout

1. **Tu es le Champion (Warsmith).** Rien ne se valide sans TOI. Chaque gate = ta signature.
2. **Tout tourne sur du Python stdlib.** Aucune installation de dépendances requise. On lance les scripts depuis leur dossier `CODEBASE/`.
3. **Le dossier `OUT/` des frégates est gitignoré** (sorties runtime). Pour livrer un pack, on le copie dans `EXPORT/` (sinon LACRIMAE ne peut pas le récupérer sur GitHub).

## 2. L'état du siège en un coup d'œil

```bash
cd MONDES_FORGES/CLIPPING/ORCHESTRATOR/CODEBASE
python3 orchestrator.py --status
```

Ou directement dans le ledger :

```bash
python3 -c "import json; d=json.load(open('MONDES_FORGES/CLIPPING/liber_clipping.json')); print('portes:', d.get('portes_validated'), '| current:', d.get('current_porte'), '| status:', d.get('campaign_status'))"
```

- `portes_validated: ['1','2','3']` → tu as validé jusqu'à la gate 3, la gate 4 est la prochaine.
- `current_porte: closed` → siège terminé.
- `campaign_status: active` → la campagne tourne.
- `campaign_status: closed` → siège isolé ; aucun résidu ne doit être repris automatiquement.

En mode MEME V2, F00 est en pause : le Champion choisit la source et F01 l’archive. Oracle présente les sorties ; le Champion est l’unique autorité des Gates.

La fermeture de la campagne est distincte de la validation d’une Gate : seul le Champion décide des Gates, puis IW_CUSTOS enregistre la clôture après l’export.

## 3. La séquence type d'un siège (résumé)

```
1. MEME V2 : déposer le post réel, sa copie, sa capture, son URL et ses métriques dans ARCHIVUM/campaign/
2. orchestrator.py --start-siege               (ouvre le siège)
3. Gate 1 : F01 source/provenance  →  valider
4. Gate 2 : angles de réaction     →  valider
5. Gate 3 : reaction_tweet + motion + métadonnées → valider
6. Gate 4 : pack source + transformation → valider → copie dans EXPORT/ → transmission à LACRIMAE
7. Après l’export : fermer le siège avec `IW_CUSTOS.py --mode close-campaign`
8. Commit + push GitHub des artefacts de production, sans secrets ni fichiers temporaires
```

Chaque étape détaillée est dans `01_MODE_LOGO_INFORMATIF.md`.

## 4. La clé premium (une seule chose à savoir)

- **Avec clé** : la clé `CLIPPING_PREMIUM_API_KEY` doit être dans API Keys (Freebuff) → les textes sont forgés par le modèle premium.
- **Sans clé (backup)** : ajoute `--oracle` à la commande F04 → l'Oracle (l'assistant) forge les textes à la main. **Le pipeline ne change pas**, tu valides exactement la même chose.

## 5. Les 3 pièges qui font perdre du temps (détail dans _PIEGES_APPRIS.md)

1. **`OUT/` gitignoré** → copie le pack dans `EXPORT/` AVANT de pousser sur GitHub.
2. **Le fair use** doit être la **clause Section 107 (EN)** — pas une vieille note d'illustration.
3. **Le résumé de la description** doit tenir en **2 lignes** (l'utilisateur valide le texte réel, pas un résumé de résumé).

## 6. Les liens utiles

| Quoi | Où |
|---|---|
| Le ledger central | `MONDES_FORGES/CLIPPING/liber_clipping.json` |
| Le log des événements | `MONDES_FORGES/CLIPPING/TRACKING/CLIPPING_LOG.md` |
| La campagne en cours | `MONDES_FORGES/CLIPPING/ARCHIVUM/campaign/` |
| Les règles logo Clipster | `MONDES_FORGES/CLIPPING/PROFILES/logo/CONTRACTS/clipping_rules_logo.md` |
| Les packs livrés | `MONDES_FORGES/CLIPPING/F05_PACKAGER/OUT/` + `EXPORT/` |

---

👉 **Tu es prêt.** Ouvre maintenant le guide du mode choisi ; pour le mode MEME, commence par `04_MODE_MEME.md`, puis lis `05_NOTE_PERTURABO_PACK_MEME.md`.


## 7. Sélecteur obligatoire du mode MEME

Lorsque le Champion demande à Oracle d’entrer en **mode MEME**, Oracle ne doit jamais supposer la version. Il doit poser exactement la question suivante :

> **Souhaites-tu utiliser MEME V1 (sourcing par mot-clé et F00 Discovery) ou MEME V2 (source tweet/Reddit fournie manuellement) ?**

### Si le Champion choisit MEME V1

Oracle charge `04_MODE_MEME.md` dans son flux historique V1 : F00 collecte les signaux multi-sources, puis les Gates sont conduites dans l’ordre documenté. Aucun passage automatique à V2 n’est permis.

### Si le Champion choisit MEME V2

Oracle charge le contrat V2 et conduit le parcours complet :

```text
1. Demander le post source, la copie, la capture, l’URL et les métriques disponibles
2. Préparer F01 et soumettre la provenance à la Gate 1
3. Attendre la validation Champion
4. Faire analyser la source et forger les angles de réaction
5. Soumettre les angles à la Gate 2 et attendre la validation Champion
6. Faire générer par F04 le reaction_tweet, le text_emotion et les métadonnées
7. Soumettre les trois éléments à la Gate 3 et attendre la validation Champion
8. Préparer F05 avec la source et la transformation séparées
9. Soumettre le pack à la Gate 4 et attendre la validation Champion
10. Exporter, transmettre et fermer uniquement après ordre explicite du Champion
```

Oracle doit annoncer la frégate active, la sortie attendue et la décision requise à chaque étape. Il ne doit ni sauter une Gate, ni valider une Gate, ni lancer la frégate suivante avant la décision explicite du Champion. En MEME V2, F00 reste en pause et F03 reste ignorée.


## 8. Composition finale du pack MEME V2

En MEME V2, la copie textuelle du tweet ou post Reddit est fournie à F01 pour l’analyse interne et la provenance. La capture PNG, qui contient déjà le tweet et son image, est l’asset visuel obligatoire du pack final. LACRIMAE l’affiche au-dessus du clip mème de sa release et produit la vidéo finale.

Le pack transmet aussi le `reaction_tweet`, le `text_emotion`, les métadonnées, le `clip_id`, le `meme_tag` et le `channel_id`. Le tag et la chaîne sont fournis par l’Opérateur. F05 assemble ; LACRIMAE rend ; aucune frégate ne doit confondre la copie interne avec la capture de production.
