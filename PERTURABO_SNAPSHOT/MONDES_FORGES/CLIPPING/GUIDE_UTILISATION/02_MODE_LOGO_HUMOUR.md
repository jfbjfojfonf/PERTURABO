# 02_MODE_LOGO_HUMOUR — (squelette, à compléter)

> Mode **logo / humour** : tu fournis une **blague** (`joke_source.json`) + une vidéo background → le forge sort N vidéos humoristiques avec logo.
> ⏳ **Pas encore testé en production.** Même squelette que `01_MODE_LOGO_INFORMATIF.md`.

---

## Ce qui DIFFÈRE du mode informatif

| Point | Mode informatif | Mode humour |
|---|---|---|
| Input principal | `article_source.json` | `joke_source.json` |
| Qui fournit les cuts | PERTURABO propose → tu valides | **Le Warsmith fournit les cuts** (`cut_source: operator`) |
| Sujet des vidéos | l'article | la blague |

## Commandes pressenties

```bash
# Gate 3 — textes (F04) : préciser le sous-mode
python3 copywriter.py --generate --angle A01 --sub-mode humour [--oracle]

# Gate 4 — pack
cd ../../F05_PACKAGER/CODEBASE
python3 packager.py --assemble --sub-mode humour --finalize
```

## Inputs spécifiques

- `ARCHIVUM/campaign/joke_source.json` — la blague (sujet + punchline + key_facts)

---

👉 **À compléter après le premier siège humour de test.** (Le fichier `_PIEGES_APPRIS.md` doit être mis à jour avec les leçons de ce mode.)
