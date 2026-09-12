# ARCHIVUM/rules/ — Savoir statique

> *Règles statiques lues par toutes les frégates. Garde-fous fondamentaux.*

---

## Fichiers attendus

| Fichier | Rôle | État |
|---|---|---|
| `whop_rules.md` | Mécanique Content Rewards (CPM, 1h, rejets) | squelette — existe à `CONTRACTS/whop_rules.md` |
| `clipping_rules.md` | Warmup, volume, FTC, transformative — hérésies | squelette — existe à `CONTRACTS/clipping_rules.md` |
| `platform_tiktok.md` | Algo TikTok + format + hook frame + sons trends + SEO commentaires | squelette (à remplir) |
| `platform_shorts.md` | Algo YouTube Shorts + swipe rate + loop + engaged views | squelette (à remplir) |
| `platform_reels.md` | Algo Reels + partages DM + saves + audio trending | squelette (à remplir) |

## Liens vers le core PERTURABO (YOUTUBE)

Les règles générales shorts vivent dans le core `MONDES_FORGES/YOUTUBE/ARCHIVUM/rules/`.
Depuis [DEV-ARCHIVUM-YOUTUBE], le Warsmith a décidé de **copier** ces règles
dans ce forge pour que les frégates CLIPPING les lisent localement (et que
OMNIS_WATCH puisse les fetcher) :

- `youtube/shorts_rules.md` — règles S1-S16 (MoneyBoyMaxx, Tim Danilov) — copie locale
- `youtube/tim_danilov_rules.md` — niche bending — copie locale

La copie est **figée au moment du transfert** (le core YOUTUBE reste la
source de vérité pour ses propres frégates ; si le core évolue, le Warsmith
re-synchronise).

## Règle anti-duplication

Le forge CLIPPING ne duplique pas le contenu du core en dehors des copies
explicites décidées par le Warsmith (voir `youtube/` ci-dessus). Seules les
règles spécifiques au clipping Whop sont créées ici (`whop_rules.md`,
`clipping_rules.md`).

---

## Template de pattern de rule

Chaque rule suit la structure des rules core (esquisse) :

```
## RÈGLE X1 : <NOM>
**Énoncé :** ...
**Application :** ...
**Validité :** ... (source, exemple observé)
**Sanction si violation :** ...
```

Voir `youtube/shorts_rules.md` pour le pattern complet.

---

## À remplir par le Warsmith

- [ ] `platform_tiktok.md` — complet
- [ ] `platform_shorts.md` — complet (peut s'inspirer du core mais doit inclure les spécificités Shorts 2026)
- [ ] `platform_reels.md` — complet
