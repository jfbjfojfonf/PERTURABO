# ORCHESTRATOR — TRACKING.md (Monde Forge CLIPPING)

> *"L'Orchestrateur ne forge pas. Il conduit les frégates de porte en porte. Chaque porte validée = one step closer à la rupture de la forteresse."*
> *Tient le ledger IW_CUSTOS + le liber_clipping.json. Synchronise les 4 portes.*

---

## RÔLE

`ORCHESTRATOR/` est la **frégate-conductrice** du forge CLIPPING. Elle ne produit pas d'artefacts viraux elle-même — elle **synchronise** les F01-F06 + TYRANT + F00_CAPTEURS et tient le **ledger central** (`IW_CUSTOS.py` dans le core PERTURABO + `liber_clipping.json` dans le forge).

Orchestre les **4 Portes**. Le Warsmith valide chaque porte manuellement.

---

## LEDGER CENTRAL — IW_CUSTOS

Aligné sur le pattern du core :
- `IW_CUSTOS.py` — script registre central (Grand Company Ledger)
- Copié dans le forge CLIPPING racine (`MONDES_FORGES/CLIPPING/IW_CUSTOS.py`)
- Enregistre l'état du siège : campagne active, porte courante, statut de chaque frégate, soumissions, fermetures

`liber_clipping.json` — état inter-frégates (partagé entre les frégates pour savoir où on en est dans le siège) :

```json
{
  "siege_id": "...",
  "campaign_id": "...",
  "campaign_status": "active|closed",
  "current_porte": "init|p1|p2|p3|p4|closed",
  "inputs_warsmith": {
    "directive_path": "...",
    "reference_clip_path": "...",
    "platform_target": "...",
    "market_target": "...",
    "n_angles": N
  },
  "fregates_status": {
    "F01_SCOUT": "pending|done|blocked",
    "F02_TYRANT_CAMP": "pending|done|blocked",
    "ANGLESMITH": "pending|done|blocked",
    "F03_SOURCE_HUNTER": "pending|done|blocked",
    "F04_COPYWRITER": "pending|done|blocked",
    "F05_PACKAGER": "pending|done|blocked",
    "F06_TRACKER": "pending|done|blocked"
  },
  "portes_validated": ["p1", "p2"],
  "packs_expedies_count": N,
  "packs_posted_count": N,
  "packs_submitted_whop_count": N,
  "last_event": "...",  
  "siege_started_at": "<ISO8601>",
  "siege_closed_at": "<ISO8601 ou null>"
}
```

---

## LES 4 PORTES

### Porte 1 — Verdict campagne

Frégates mobilisées : F01_SCOUT (alimentation) + F02_TYRANT_CAMP (verdict)

Avant la Porte 1 (optionnel mais recommandé) : F00_CAPTEURS scan écosystème + niche

Le Warsmith valide le verdict GO/NO-GO. Si NO-GO → campaign pas poursuivie. Si GO → Porte 2.

```
orchestrator.py --gate 1 --decision valide|rejette
```

### Porte 2 — N angles forgés

Frégates mobilisées : ANGLESMITH (peut être porté par F02 ou dédié — voir implémentation future)

L'Orchestrateur déclenche la forge des N angles. Le Warsmith voit les N angles (direct + océan bleu), valide ou tue 1+ angles (rereforge si kill).

→ `OUT/angles.json` validé → Porte 3.

```
orchestrator.py --gate 2 --decision valide
# Si angles rejetés :
orchestrator.py --gate 2 --decision rejete --angle <angle_id> --reason "..."
# → ANGLESMITH re-forge un angle de remplacement
```

### Porte 3 — Source specimens + text payloads

Frégates mobilisées : F03_SOURCE_HUNTER (source par angle) + F04_COPYWRITER (texte par angle)

Pour chaque angle, F03 sélectionne l'asset + segments puis F04 forge le text_payload complet. Le Warsmith + l'IRON ordonnancement valident les N text_payloads.

→ N `source_specimen_<angle>.json` + N `text_payload_<angle>.json` (et `.md` pour le Warsmith).

```
orchestrator.py --gate 3 --decision valide
```

### Porte 4 — N production packs expédiés → LACRIMAE

Frégate mobilisée : F05_PACKAGER

Ces N `production_pack_<angle>.json` sont livrés à LACRIMAE (par raw.githubusercontent.com URL — point d'intégration existant).

F06_TRACKER prend le relais post-publication.

```
orchestrator.py --gate 4 --decision valide
# → distribue packs_index.json vers LACRIMAE (via git push ou raw URL)
# → F06_TRACKER démarre
```

---

## PATTERN D'EXÉCUTION — COMMANDES PRINCIPALES

```
# Démarrage d'un siège (campagne active)
orchestrator.py --start-siege --directive ARCHIVUM/campaign/directive.md \
   --reference-clip ARCHIVUM/campaign/reference_clip.json \
   --platform youtube --market us_young_english \
   --n-angles 10
# → Initialise liber_clipping.json
# → Statut = "init", en attente de F00_CAPTEURS warpping et Porte 1

# Après chaque porte :
orchestrator.py --gate N --decision valide
# → Avance current_porte à la suivante
# → Active les frégates de la prochaine porte

# Reprise après une pause :
orchestrator.py --resume
# → Lit liber_clipping.json, identifie la porte courante, indique 
#   au Warsmith comment reprendre

# Fermeture campaigne :
orchestrator.py --close-siege --final-payout-summary ...
# → Marque siehe comme closed, déclenche F06 agrégation learnings
# → Libère la campaign/ pour la suivante (archivage optionnel)
```

---

## CONTRATS RÉFÉRENCÉS

- `HERESIE/CONTRACTS/iron_prompt.md` (core, lien) — pattern prepare/IRON/finalize
- `HERESIE/CONTRACTS/system_prompt.md` (core, lien) — boussole système
- `CONTRACTS/anti_bullshit.md` (core, lien)
- Tous les `ARCHIVUM/rules/`

---

## DÉPENDANCES

- **Amont** : Le Warsmith (4 inputs initiaux)
- **Réseau interne** : toutes les frégates F01-F06, TYRANT, F00_CAPTEURS
- **Downstream** : LACRIMAE (recoit les packs via Porte 4), `ARCHIVUM/learnings/learnings.json` (à la fermeture)

---

## HÉRÉSIES

- ❌ Passer une porte sans validation Warsmith explicite
- ❌ Sauter une porte (séquence Porte 1 → 2 → 3 → 4 obligatoire)
- ❌ Auto-fermer une siège (seul le Warsmith déclare la fin)
- ❌ Démarrer un nouveau siège sans fermer le précédent (campaign/ est singulier)
- ❌ N'importe quelle frégate modifie directement `IW_CUSTOS.py` sans passer par l'Orchestrateur (chaque frégate appelle check-in mais c'est l'Orchestrateur qui tient la cohérence)

---

## STATUT

| Phase | État | Notes |
|---|---|---|
| Arborescence créée | ✅ | |
| TRACKING.md rédigé | ✅ | Ce fichier |
| Code Python implémenté | ✅ | v1 — voir `[DEV-ORCHESTRATOR]` dans `TRACKING/CLIPPING_LOG.md` |
| `orchestrator.py` | ✅ | CLI multi-commandes (start-siege/resume/gate/close/status) |
| `libs/ledger_manager.py` | ✅ | Gère liber_clipping.json + IW_CUSTOS.py |
| `libs/gate_validator.py` | ✅ | Vérifie que les outputs attendus sont présents avant validation de porte |
| `libs/siege_initializer.py` | ✅ | Valide les 4 inputs Warsmith + blocage si campagne active |
| `libs/omnis_watch_distributor.py` | ✅ | packs_index.json + raw URLs pour LACRIMAE |
| `gates.py` | ✅ | Les 4 Portes du forge CLIPPING (verdict/angles/textes/packs) |
| `requirements_orchestrator.txt` | ✅ | Standard lib — aucune dépendance externe |

Référence d'implémentation : `HERESIE/ORCHESTRATOR/CODEBASE/orchestrator.py` dans le core (probable réutilisation à 60-70%, adaptation pour les 4 Portes du forge clipping et la spécificité de F04).

*Fer au-dedans, Fer au-dehors. L'Orchestrateur ne ment pas — il conduit.*


## Addendum MEME V1/V2 — sélection et conduite Oracle

Quand le Champion demande le mode MEME, l’Orchestrator ou Oracle doit demander explicitement `MEME V1` ou `MEME V2` avant toute initialisation. La version choisie doit être enregistrée dans le contexte du siège et ne peut pas changer sans décision explicite du Champion.

- **MEME V1** : flux historique par mot-clé et Discovery F00, puis angles, F04 et F05.
- **MEME V2** : F00 en pause ; le Champion fournit `source_post.text`, capture, URL, auteur, date et métriques ; F01 archive et contrôle ; F02/ANGLESMITH forge les angles ; F04 produit `reaction_tweet`, `text_emotion` et métadonnées ; F05 assemble source et transformation.

En MEME V2, les portes sont conduites dans cet ordre : Gate 1 source/provenance, Gate 2 angles, Gate 3 réaction + motion + métadonnées, Gate 4 pack. Oracle doit annoncer la frégate active, la sortie attendue et la décision requise, puis attendre la validation Champion. Il est interdit de sauter une porte, de lancer la frégate suivante par anticipation ou de déclarer une validation au nom du Champion.

En MEME V2, la copie textuelle de la source reste un input interne F01. La capture PNG, qui contient le tweet et son image, est l’asset final transmis à LACRIMAE. Le pack de Porte 4 doit aussi contenir le `clip_id`, le `meme_tag` et le `channel_id` fournis par l’Opérateur, ainsi que le `reaction_tweet`, le `text_emotion` et les métadonnées. LACRIMAE assemble la capture au-dessus du clip mème de sa release et produit la vidéo finale ; F05 ne rend pas la vidéo.
