# CLIPPING RULES — Règles du clipping Whop Content Rewards

> * STATUT : SQUELETTE — Le Warsmith doit enrichir. *

Ce document est le **garde-fous fondamental** du forge CLIPPING. Toutes les frégates le lisent comme anti_bullshit.md est lu dans le core. Il code les hérésies spécifiques au clipping Whop.

---

## RÈGLE C1 — STRICT-SOURCE (La Source Sacrée)

**Énoncé** : La source d'un clip ne provient **que** des assets fournis par la campagne Whop. Aucune source externe, aucune adjacence, aucun "scrap complémentaire".

**Application** : F01_SCOUT inventorie exclusivement les assets de `directive.md`. Toute sortie du périmètre est hérésie.

**Sanction si violation** : rejet Whop + ban possible + perte de crédibilité avec la marque.

---

## RÈGLE C2 — DISCLOSURE FTC OBLIGATOIRE

**Énoncé** : Tout clip porte la mention `#ad` ou `#sponsored` visible dans la caption, AVANT le "voir plus".

**Application** : F04_COPYWRITER inclut dans tous les `caption`. F05_PACKAGER vérifie dans `COMPLIANCE.disclosure`.

**Sanction si violation** : rejection Whop + shadowban platform (TikTok notamment).

---

## RÈGLE C3 — SOUMISSION DANS L'HEURE (Règle critique Whop)

**Énoncé** : Le premier soumission Whop doit intervenir dans l'heure qui suit la publication du clip.

**Application** : `submission_checklist` activée par F06_TRACKER avec `deadline_min: 60`. Flag si en retard (`submission_within_1h: false`).

**Sanction si violation** : rejet Whop (règle publique).

---

## RÈGLE C4 — TRANSFORMATIVE OBLIGATOIRE (Reused Content policy)

**Énoncé** : Le clip doit être "transformative" — ajouter narrative, commentary, editing. Pas de copie brute de la source.

**Application** : PERTURABO forge des **angles d'attaque** (et non des copies directes) — reframing, émotion, engagement. Le rendu (OMNIS_WATCH) applique le reste (cut, captions, sound design).

**Sanction si violation** : rejection Whop + demonetization platform (YouTube notamment).

---

## RÈGLE C5 — WARMUP COMPTES (Anti-shadowban platform)

**Énoncé** : Les nouveaux comptes platform (TikTok / IG / YT) sont shadowban par défaut pendant 7-14 jours. Il faut farmer (warmup) avant de poster les clips de campagne.

**Application** :
- `ARCHIVUM/channels/<account_slug>/identity.json` contient `warmup_status` + `account_age_days`.
- F06_TRACKER lit le warmup status avant de valider un post — si `warmup` < 7 jours → flag warning `WARMUP_INCOMPLETE`.

**Sanction si violation** : 0 view jail. Le clip ne sort pas du FYP.

---

## RÈGLE C6 — VOLUME + MULTI-PLATEFORME

**Énoncé** : Volume de production = 10-20 clips/jour en batch. Multi-plateforme (même clip → TikTok + Reels + Shorts).

**Application** :
- Un angle → un pack par plateforme (pas multi-plateforme dans un même pack)
- Pour N angles × M plateformes = N×M packs potentiels (le Warsmith décide combien de plateformes par angle)

---

## RÈGLE C7 — TRACKING UTM / BITLY (Négociation CPM)

**Énoncé** : Utilisation de liens trackés (UTM, Bitly) pour prouver les perfs et négocier meilleurs taux côté Whop.

**Application** : F06_TRACKER génère le lien tracké au moment de la soumission Whop.

---

## HÉRÉSIES SPÉCIFIQUES AU CLIPPING WHOP (Récap des interdictions absolues)

- ❌ Source non-issue des assets campaign (règle C1)
- ❌ Clip non-transformative (règle C4)
- ❌ Disclosure FTC absent (règle C2)
- ❌ Soumission > 1h après post (règle C3)
- ❌ Compte non-warmupé qui post (règle C5)
- ❌ Variation directe du clip de référence (le clip ref = matière première brute, pas modèle à cloner — décision Warsmith)
- ❌ Re-ciblage océan bleu au-delà de 1 couche de profondeur
- ❌ Auto-posting / auto-submitting (le Warsmith poster — pas le système)
- ❌ Scraper F00_CAPTEURS en automatique (commandité uniquement)
- ❌ "Abonne-toi" / "Like et partage" / "Swipe up" / fadeouts / silences > 3s

---

## STATUT DE REMPLISSAGE

| Section | État |
|---|---|
| C1 Strict-source | documenté |
| C2 Disclosure FTC | documenté |
| C3 Soumission 1h | documenté |
| C4 Transformative | documenté |
| C5 Warmup comptes | documenté (structure) |
| C6 Volume + multi-plateforme | documenté (chiffres à confirmer) |
| C7 Tracking | documenté |
| Hérésies spécifiques | documenté |

**À enrichir par le Warsmith** : cas particuliers, exemples, sanctions observées en production.

Référence couplage : `HERESIE/CONTRACTS/anti_bullshit.md` (core).
