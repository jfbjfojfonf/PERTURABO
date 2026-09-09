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
4. **Gate hybride** — score ≥ 8.5 + intensité ≥ 0.9 → auto-approuvé (le live n'attend pas) ; le reste en file d'attente Warsmith.
5. **Clips Helix en direct** — capture serveur immédiate au moment détecté (secrets `TWITCH_TOKEN` + `TWITCH_CLIENT_ID`) ; sans token : timestamps seuls + segment VOD extrait après le live.
6. **Board GitHub Pages** — `BOARD_LIVE/index.html` lit `data/live_status.json` (poussé par le radar toutes les 3 min). Consultable au téléphone.
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
- [ ] **Secrets GH présents** : `TWITCH_TOKEN`, `TWITCH_CLIENT_ID` (Settings → Secrets).
- [ ] **Pages actives** : le board répond sur `https://kioka8877-ux.github.io/PERTURABO/` ?
- [ ] **Fusion v2 → main ?** Si le radar a fait ses preuves sur plusieurs sessions :
      refusionner `chat_pulse` dans `main` comme lib optionnelle (elle ne casse rien :
      c'est juste un producteur de signaux en plus). La branche peut alors dormir.

---

## ⚠️ Règle de sources (campagnes)

Le radar **n'écoute que les chaînes autorisées par les campagnes actives**
(règles de source des directives Clipify : « streams à partir du… », « pas de reaction clips », etc.).
Écouter une chaîne hors campagne = clip non soumissible = travail perdu. Respecter la directive.

---

## 🧱 Ce qu'il reste avant le premier vrai live

1. Secrets GH : `TWITCH_TOKEN` (scope `clips:edit`) + `TWITCH_CLIENT_ID` — sans eux le radar
   fonctionne en timestamps seuls (pas de clip serveur immédiat).
2. Activer GitHub Pages (Settings → Pages → branch `v2-live`, dossier `BOARD_LIVE` ou `/`).
3. Une session de test sur un live réel pour calibrer `min_rate` / `spike_factor`
   (une grande chaîne ≠ une petite : la baseline EMA s'adapte, mais les seuils se peaufinent).

---

*IV Légion — le Fer qui Veille, maintenant en temps réel.*
