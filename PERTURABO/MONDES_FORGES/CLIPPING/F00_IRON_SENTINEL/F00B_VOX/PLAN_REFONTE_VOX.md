# PLAN_REFONTE_VOX — Refonte de l'architecture F00B_VOX

> **Statut : ✅ IMPLÉMENTÉ (P1→P6 + tous capteurs).** Clips/audio/visuel/emotes/événements/lexical branchés. Reste validation run réel. Document de référence avant toute ligne de code.
> Ne rien modifier ici sans revalidation du Warsmith.
>
> Figé : la partie **Modal** (transcribe.py, workflow GH Actions, secrets) est un succès acté.

---

## 1. Principe structurant

**Garbage in = Garbage out.** VOX est le premier maillon ; il ne garantit pas la viralité
finale (le titre et le montage le feront en aval), il garantit le **MOMENT**.

Trois filtres se combinent, jamais séparément :
1. **Émotion** — le moment a réellement créé une réaction.
2. **Statistique lexicale** — le moment est exploitable en texte (densité, trous, hook, arc).
3. **Directive campagne (COMPLÈTE)** — le moment est autorisé (source, plateforme, marché, cycle, exclusions).

VOX est un **garde-barrière**, pas un juge final : il rejette pour 3 raisons différentes,
et il doit **expliquer pourquoi** (rejection_reasons).

---

## 2. L'entonnoir à 4 étages (le premium ne voit jamais le flot brut)

| Étage | Contenu | Coût | Sortie |
|---|---|---|---|
| **0** | Capteurs gratuits (emotes+vélocité, clips commu, événements, stats) — scan total | ~0 | 50-80 fenêtres chaudes |
| **1** | Filtres lexicaux + directive campagne complète | ~0 | 15-25 fenêtres exploitables |
| **2** | Capteurs lourds ciblés (audio, visuel) — seulement sur les survivantes | chirurgical | 8-12 candidats |
| **3** | Arbitrage premium (kimi-k3) — reframing sémantique + verdict | 8-12 appels | 2-3 finalistes |
| **Gate** | Warsmith valide | humain | — |

---

## 3. La flotte de capteurs F00B_VOX

F00A a ~14 capteurs ; VOX n'en a aucun (d'où le `intensity:0.9` en dur, auto_detector.py l.380).

### Étage 0 — gratuit (scan total)
- **Émotes + vélocité** : valence (KEKW, PogChamp, LUL…), accélération, copypasta/spam → remplace `chat_count`.
- **Clips communautaires (heatmap)** : densité de clips ≠ playeurs + vues cumulées + **titres déjà écrits**.
  L'intersection densité × vues = signal le plus fort. Offsets → géolocalisation timeline.
- **Événements (UserNotice)** : raids, hosts, gift subs, followers.
- **Stats externes** : viewership (SullyGnome / StreamsCharts).

### Étage 1 — lexical (gratuit)
- Densité de parole · trous > 3 s · hook positionnel 0-3 s · arc à un seul pic.
- **Directive campagne complète** en veto (source / plateforme / marché / cycle / exclusions).

### Étage 2 — lourd ciblé
- **Audio** : rire / applaudissement / silence (modèle audio dédié, pas la clé NVIDIA).
- **Visuel** : visage speaker / cut / action (frames ffmpeg, règle « hook = visage », pur_directive).

---

## 4. Tableau brut & scoring

Une ligne par fenêtre (~5-10 s), chaque capteur = une colonne. Le scoring lit CE tableau
(auditable), plus jamais un signal unique deviné.

Pondération cible : hook 0.25 · convergence capteurs 0.25 · lexical 0.20 · émotion 0.15
· conformité campagne = **dur (0/1, veto)**.

Vetos non négociables : source hors périmètre · silence > 3 s · zéro mot en 0-3 s ·
2 pics d'énergie égaux · sujet exclu.

---

## 5. Clé premium (kimi-k3) — périmètre exact

**Fait (cerveau) :** score sémantique « potentiel de reframing » (hooks_pur.json) +
analyse transcript/chat/titres de clips + arbitrage final sur le tableau.

**Ne fait pas (yeux/oreilles) :** extraction frames (ffmpeg) · détection rire audio
(modèle dédié) · vision (accès par-compte, 404 possibles).

---

## 6. Ordre de build (phases)

- **P1** — ✅ **FAIT** — Schéma tableau brut + directive campagne complète en veto (`libs/campaign_veto.py`, branché dans `run_auto_detect`).
- **P✅2** — Capteurs gratuits (étage 0) → remplace `intensity:0.9`.
- **P✅3** — Filtres lexicaux (étage 1), alignés pur_directive + hooks_psychology.
- **P✅4** — Capteurs lourds ciblés (étage 2), audio puis visuel.
- **P✅5** — Arbitrage premium (étage 3), kimi-k3.
- **P✅6** — Scoring/fusion + docs/tracking, Gate Warsmith voit le tableau.

Chaque phase est livrable, testable et commitable indépendamment.

---

*Intensité = convergence pondérée de 4-6 capteurs indépendants, plus jamais une constante.*
