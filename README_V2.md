# PERTURABO v2-live — La Branche du Live

> *« Le VOD est le passé. Le live est maintenant. »*
> — VOX, Oreille Absolue, version temps réel

---

## 🎯 Mission de la branche

| Branche | Mode | Entrée | Quand l'utiliser |
|---|---|---|---|
| `main` | PUR (VOD) | VOD Twitch passée | Tu as le temps, le stream est fini |
| **`v2-live`** | PUR (LIVE) | Stream en cours | Tu veux sortir les clips **pendant** le live |

**Tout le reste est identique** : F04 (copywriting), F06 (montage), patterns, campagnes,
watermarks, bras armé (OMNIS_WATCH). La SEULE divergence est la couche d'entrée de VOX :
le Radar (`chat_pulse`) capte les moments en direct, là où `f00b_vox.py` analyse des VOD passées.

Le pipeline de sortie (`candidats` → `scoring` → `gate` → `trail.json`) produit des fichiers
**au même schéma** que le mode VOD. F04 et F06 ne voient aucune différence.

---

## 🔒 Les 7 décisions figées (validées par le Warsmith)

1. **Branche `v2-live`** = copie exacte de `main` (base `8ee8c8b`). Seule divergence : la couche live de VOX.
2. **Radar sur GitHub Actions** — `workflow_dispatch`, multi-chaînes (un IRC par chaîne), 6h max par job, gratuit.
3. **Oracle en cron 5 min** — détecte les lives via Helix, ouvre une issue `[ORACLE][chaîne]`, le Warsmith valide, le radar se lève.
   ⚠️ **Piège GitHub** : un cron ne tourne QUE sur la branche par défaut du repo.
   Pour que l'Oracle se réveille tout seul, `v2-live` doit être la branche par défaut
   (Settings → Branches → switch default branch — ça ne touche pas à `main`, c'est
   réversible). Sinon : lancer l'Oracle à la main (Run workflow) quand tu veux vérifier.
4. **Gate hybride** — score ≥ 8.5 + intensité ≥ 0.9 → auto-approuvé (le live n'attend pas) ; le reste en file d'attente Warsmith.
5. **Clips Helix en direct** — capture serveur immédiate au moment détecté (secrets `TWITCH_TOKEN` + `TWITCH_CLIENT_ID`) ; sans token : timestamps seuls + segment VOD extrait après le live.
6. **Board GitHub Pages** — `docs/index.html` lit `data/live_status.json` (poussé par le radar toutes les 3 min). Consultable au téléphone. Pages sert le dossier `/docs` de la branche `v2-live`.
7. **Le Warsmith reste le dernier contrôle humain** — la machine produit, l'humain publie.

---

## 🚀 Lancer une session (le flow complet)

```
1. Oracle détecte le live → issue [ORACLE][chaîne] ouverte (cron 5 min)
2. Toi : Actions → "PERTURABO LIVE RADAR (v2-live)" → Run workflow
       channels = la chaîne, duration_min = 240 max 330
3. Le radar écoute le chat — TOUT SEUL (baseline 5 min, pics, clip pressure)
4. Moment détecté → clip Helix capté IMMÉDIATEMENT → scoring VOX → gate hybride
       ⚡ excellent → auto-approuvé → trail.json (trail immédiat)
       🚪 moyen   → file d'attente → board + OUT/gate_live.json
5. Fin de session : artefacts OUT archivés + statut board committé
6. Toi : valide la file (guide 18, section 5) → F04 → F06 → bras armé → TU POSTES
```

**En résumé : ton seul travail en live = valider la file depuis ton téléphone et poster.**

---

## 📅 Checklist hebdomadaire (le rappel demandé)

À faire **une fois par semaine**, en entrant sur la branche :

- [ ] **Le token CUT est-il publié ?** Adresse du token + paire avec liquidité sur un DEX ?
      Si oui : réévaluer CutChain comme layer de paiement (le radar `chat_pulse` est notre
      version indépendante, on ne dépend d'eux pour rien).
- [ ] **Les campagnes actives** : quelles chaînes sont autorisées cette semaine ?
      Mettre à jour `IN/live_input.example.json` + `IN/oracle_input.example.json`.
- [ ] **Les 4 secrets GH présents et valides** (Settings → Secrets → Actions) :
      `TWITCH_CLIENT_ID` (fixe), `TWITCH_CLIENT_SECRET` (fixe), `TWITCH_REFRESH_TOKEN`
      (longue durée) et `TWITCH_TOKEN`. Les workflows **rafraîchissent le token tout
      seuls à chaque run** (`refresh_twitch_token.py`) : plus besoin d'y toucher, SAUF si
      l'Oracle/le radar loggent « Refresh échoué » → alors seulement régénérer le token
      via twitchtokengenerator.com (avec notre client ID/secret) et remettre à jour
      `TWITCH_TOKEN` + `TWITCH_REFRESH_TOKEN`.
- [ ] **Pages actives** : le board répond sur `https://kioka8877-ux.github.io/PERTURABO/` ?
      (Settings → Pages → source = branche `v2-live`, dossier `/docs`)
- [ ] **PAS de fusion v2 → main.** Décision du Warsmith : `main` reste la forge VOD
      (elle est déjà pleine). `v2-live` vit sa vie sur sa propre branche. Si un jour le
      radar fait ses preuves, on peut *copier* `chat_pulse` dans `main` comme lib
      optionnelle — jamais de merge de branches.

---

## ⚠️ Règle de sources (campagnes)

Le radar **n'écoute que les chaînes autorisées par les campagnes actives**
(règles de source des directives Clipify : « streams à partir du… », « pas de reaction clips », etc.).
Écouter une chaîne hors campagne = clip non soumissible = travail perdu. Respecter la directive.

---

## 🧱 Ce qu'il reste avant le premier vrai live

1. Secrets GH : les 4 (`TWITCH_CLIENT_ID`, `TWITCH_CLIENT_SECRET`, `TWITCH_REFRESH_TOKEN`,
   `TWITCH_TOKEN` scope `clips:edit`) — sans eux le radar fonctionne en timestamps seuls
   (pas de clip serveur immédiat). Le token user vit ~4 h : le refresh est automatique
   au début de chaque run (`refresh_twitch_token.py`).
   ⚠️ Sessions #2 et #3 : le refresh a échoué (`invalid client secret`) → la valeur de
   `TWITCH_CLIENT_SECRET` dans GitHub n'est pas la bonne. À corriger via dev.twitch.tv →
   Manage → « Nouveau secret » → Update du secret dans GH.
2. Activer GitHub Pages (Settings → Pages → branch `v2-live`, dossier `/docs`).
3. Une session de test sur un live réel pour calibrer `min_rate` / `spike_factor`
   (une grande chaîne ≠ une petite : la baseline EMA s'adapte, mais les seuils se peaufinent).
4. **Helix : premier clip serveur à conquérir.** Session #3 : 10/10 clips refusés par
   Twitch (`HTTP 500`). Le clipper expose maintenant le corps des réponses d'erreur —
   la prochaine session dira la vraie raison (suspicions : rate limit / app en trop jeune
   / quota). Le pipeline lui-même est prouvé : 10 moments → 10 scorings → 10 approvals.
5. ~~**Calibration du scoring live**~~ ✅ **FAIT (2026-09-10)** — `compute_score_live()` :
   chaque critère VOX est alimenté par la force RÉELLE du pic (ratio rate/baseline,
   hystérie des mots chauds, clip_pressure, durée) au lieu du profil fixe. Preuve sur
   les 10 moments de la session #3 : écart 0.0 → **3.25** (9.75 pour ratio ×5.56,
   6.5 pour les pics faibles). Effet voulu : seuls les gros pics passent l'auto-
   approbation (8.5), les moyens partent en file Warsmith. Moteur VOD de main intact.
   Chaque score est publié en direct sur le board (détail des 6 critères).
6. ~~**Câbler les règles de campagne dans le radar live**~~ ✅ **FAIT (2026-09-10)** —
   Garde de Fer en place : `ARCHIVUM/campaign/live_campaigns.json` (registry chaîne →
   campagne) + `libs/campaign_gate.py`. Au lancement, chaque chaîne est résolue
   (campagne / cycle expiré / hors campagne), le mode `mixed` est **refusé**, et chaque
   verdict porte `campaign_eligible` + `campaign_id` (propagés vers artefacts + board).
   Override opérateur possible via l'input `mode_override` du workflow (auto /
   technical_test / campaign). ⚠️ Le cycle Sofey étant expiré, toute session sur
   `aishahsofeyy` ressort pour l'instant `technical_test` — renouveler la directive Whop
   pour passer en campagne réelle.

---

## 🖥 La Salle de Contrôle du Siège (board v2)

`docs/index.html` est désormais une salle de contrôle Iron Warriors (palette
Boltgun Metal / Leadbelcher / Shining Gold / noir, bandes hazard, logo ⟨/⟩ SVG) :

- **🗺 Carte du siège** — un secteur fortifié par chaîne (SVG), la muraille pulse
  en or quand le chat s'enflamme (ratio ≥ 2.5)
- **🎯 Scoreur en direct** — chaque obus scoré avec jauge or 0→10, détail des
  6 critères (grâce au scoring calibré), tampon APPROUVÉ / EN FILE / REJETÉ
- **📜 Manifeste des clips** — les pièces Helix captées avec lien cliable
  immédiat, ou mention « timestamps seuls » si Helix indisponible
- **🚪 Ordres en attente** — la file Warsmith à valider (depuis le téléphone)
- **📡 Télémétrie** — lampes phosphore connecté/hors-ligne, ratio ×baseline
- Horloge de siège, badge Garde de Fer, citation du maître du siège

Données : le radar pousse `recent_scored` + `clips` dans `live_status.json` à
chaque tick — le board se rafraîchit toutes les 60 s.

---

## 🧾 Journal des sessions (v2-live)

| # | Date (UTC) | Chaîne | Résultat |
|---|---|---|---|
| 1 | 2026-09-10 | e11ysa (60 min) | Pipeline OK, 0 message — bug SSL `chat_pulse.py` trouvé et corrigé |
| 2 | 2026-09-10 | fps_shaka (45 min) | Tuée par le step refresh (`invalid client secret`) → refresh rendu non bloquant |
| 3 | 2026-09-10 | fps_shaka (45 min) | ✅ 10 moments détectés, 10 scorés, 10 approuvés — 0 clip Helix (`HTTP 500`, cause à confirmer) |

---

*IV Légion — le Fer qui Veille, maintenant en temps réel.*
