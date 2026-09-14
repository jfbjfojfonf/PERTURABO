# 03_MODE_WHOP — (squelette, à compléter)

> Mode **whop / clip canon** : le flux CLIPPING classique (F01 → F02 → F03 → F04 → F05) sur un clip de référence → production packs pour une campagne Whop.
> ⏳ **Pas encore testé en production.** Même squelette que `01_MODE_LOGO_INFORMATIF.md`.

---

## Ce qui DIFFÈRE des modes logo

| Point | Mode logo | Mode whop |
|---|---|---|
| Profil | logo (Clipster) | whop (campagne monétisée) |
| F03 SOURCE HUNTER | **skippé** | **actif** (sélection asset + segments dans le clip) |
| Logo | GIF campagne | pas de logo (ou spécifique campagne) |
| Cuts | PERTURABO / opérateur | issus de F03 |

## Commandes pressenties

```bash
# Gate 3 — F03 + F04
cd ../../F03_SOURCE_HUNTER/CODEBASE
python3 source_hunter.py --auto --angles ../../F02_TYRANT_CAMP/OUT/angles.json --finalize

# Gate 4 — pack (sans --sub-mode ou --sub-mode défaut)
cd ../../F05_PACKAGER/CODEBASE
python3 packager.py --assemble --finalize
```

---

👉 **À compléter après le premier siège whop.** (Le fichier `_PIEGES_APPRIS.md` doit être mis à jour avec les leçons de ce mode.)
