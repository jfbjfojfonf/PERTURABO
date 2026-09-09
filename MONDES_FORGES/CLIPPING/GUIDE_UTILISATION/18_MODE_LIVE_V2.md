# 18 — MODE LIVE v2 (branche v2-live)

> Le mode PUR en temps réel. Tu n'analyses plus une VOD finie : tu écoutes le live,
> tu sors les clips pendant que le stream tourne encore. Même scoring, même F04/F06,
> même bras armé — seule l'entrée change.

---

## 1. Le but en 3 lignes

Le Radar (`chat_pulse`) écoute le chat Twitch en anonyme (aucun token pour lire),
mesure la vitesse du chat vs une baseline de 5 minutes, et détecte les **moments**
(pics + « clip pressure »). Chaque moment devient un candidat scoré par le moteur VOX
exact, passé au **gate hybride** : les excellents partent en trail immédiatement,
le reste attend ta validation. À la fin, `trail.json` alimente F04/F06 comme en VOD.

## 2. Les pré-requis (une seule fois)

| Quoi | Où | Sans ça |
|---|---|---|
| `TWITCH_TOKEN` (scope `clips:edit`) | Secrets GitHub | Pas de clip serveur immédiat (timestamps seuls) |
| `TWITCH_CLIENT_ID` | Secrets GitHub | idem |
| GitHub Pages activé (branche `v2-live`) | Settings → Pages | Board inaccessible (le radar tourne quand même) |

## 3. Le flow d'une session

```
Oracle (cron 5 min) → issue [ORACLE][chaîne] "LIVE — valider ?"
        ↓ TOI (validation, 30s)
Actions → PERTURABO LIVE RADAR (v2-live) → Run workflow
        ↓
Radar : IRC anonyme par chaîne · baseline 5 min · pics · clip pressure
        ↓ MOMENT
Clip Helix capté IMMÉDIATEMENT (le stream continue)
        ↓
Scoring VOX (6 critères, moteur inchangé)
        ↓
GATE HYBRIDE
   ├─ score ≥ 8.5 ET intensité ≥ 0.9 → ⚡ auto-approuvé → trail
   └─ sinon (≥ 6.0)                  → 🚪 file Warsmith (board + téléphone)
        ↓ FIN DE SESSION
trail.json + artefacts OUT → F04 → F06 → bras armé → TU POSTES
```

## 4. Lancer la session (commandes exactes)

**Way 1 — l'Oracle te prévient** (recommandé) : l'issue `[ORACLE][chaîne]` apparaît,
tu vas dans **Actions → PERTURABO LIVE RADAR (v2-live) → Run workflow** :
- `channels` : `aishahsofeyy` (plusieurs : `aishahsofeyy,autreChaine` — sans espaces)
- `duration_min` : 240 (max 330, limite 6h du job)

**Way 2 — tu sais déjà qu'il est live** : directement Run workflow.

**Way 3 — local (test)** :
```bash
cd MONDES_FORGES/CLIPPING/F00_IRON_SENTINEL/F00B_VOX
cp IN/live_input.example.json IN/live_input.json   # éditer les chaînes
cd CODEBASE && python3 f00b_vox_live.py
```

Pendant la session : le statut est poussé sur `BOARD_LIVE/data/live_status.json`
toutes les 3 min → le board (`index.html`) se rafraîchit depuis ton téléphone.

## 5. Valider la file d'attente Warsmith

Les auto-approuvés sortent pendant le live. La file se valide **en fin de session**
(ou en cours, depuis les artefacts) avec le flux VOD habituel :

```bash
cd MONDES_FORGES/CLIPPING/F00_IRON_SENTINEL/F00B_VOX
# 1. Récupérer les artefacts OUT de la session (artefact Actions "vox-live-session")
# 2. Brancher les fichiers live sur le flux gate standard :
cp OUT/scoring_live.json OUT/scoring.json
cp OUT/gate_live.json   OUT/gate_verdict.json
# 3. Éditer OUT/gate_verdict.json : pending_warsmith → approved / rejected (motif !)
# 4. Régénérer le trail complet (auto-approuvés + tes validations) :
python3 CODEBASE/f00b_vox.py trail
```

## 6. Le relai au bras armé (identique VOD)

`OUT/trail.json` produit → même enchaînement qu'en PUR :
`pur_montage_pipeline.py` (VOX + F04) → packs `production_pack_*.json` →
`EXPORT/` → gate Warsmith → OMNIS_WATCH rend la vidéo → **tu postes**.
Rien à apprendre : c'est le pipeline VOD, avec des candidats tout frais.

## 7. Les règles verrouillées

- **Sources de campagne** : le radar n'écoute que les chaînes autorisées par les
  directives actives. Hors campagne = non soumissible.
- **Pas de trail sans verdict** (auto ou Warsmith) — comme en VOD.
- **Cooldown 120s par chaîne** : pas de doublons de moments.
- **6h max par job** : `duration_min` ≤ 330 (marge de commit).
- **Budget transcription** : la transcription des segments reste sur Modal (burst GPU,
  centimes) — le radar lui-même est gratuit (IRC + Actions).

## 8. Checklist rapide avant chaque session

- [ ] La chaîne est-elle autorisée par une campagne active ?
- [ ] Secrets `TWITCH_TOKEN`/`TWITCH_CLIENT_ID` présents ?
- [ ] `duration_min` ≤ 330 ?
- [ ] Board accessible (ou artefacts Actions en secours) ?
- [ ] Après session : file validée → `trail` → F04/F06 → EXPORT → gate → bras armé.

---

*Guide v2-live — le Fer qui Veille, en temps réel.*
