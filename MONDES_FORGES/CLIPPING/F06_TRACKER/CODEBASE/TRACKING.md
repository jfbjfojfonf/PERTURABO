# F06_TRACKER — TRACKING.md

> *"Le siège n'est fin que lorsque la forteresse a rendu compte. Le tracker ne dort pas."*
> *Frégate post-publication. Active, pas passive. Boucle le learnings.json et ferme la campagne.*

---

## RÔLE

F06_TRACKER est la **frégate post-Pote 4**. Elle prend le relais après que les N `production_pack.json` ont été expédiés à OMNIS_WATCH. Pour chaque pack posté par le Warsmith, elle :
1. Active la `submission_checklist`
2. Enregistre la soumission (<1h ou en retard — flag si en retard)
3. Logge les vues à 1h + 24h (relevés saisis par le Warsmith ou via API si disponible en v2)
4. Calcule le payout réel observé vs seuil
5. Nourrit `ARCHIVUM/learnings/learnings.json`
6. À la fermeture de campagne (déclarée par le Warsmith), agrège les résultats cumulés et active la pondération future de ANGLESMITH (seuil 50 packs).

---

## INPUTS

| Input | Source | Format | Obligatoire |
|---|---|---|---|
| `production_pack_<angle>.json` (N) | F05_PACKAGER (Porte 4) | JSON N | ✅ |
| Noms de compte publiés | Warsmith (saisie manuelle au moment de poster) | string | ✅ |
| Vues à 1h | Warsmith (saisie manuelle — API pas encore disponible en v1) | int | ✅ |
| Vues à 24h | Warsmith | int | ✅ |
| Payout réel | Warsmith (depuis dashboard Whop) | float | ✅ |
| Déclaration "fin de campagne" | Warsmith | booléen | Pour clôturer |

---

## OUTPUTS

### `OUT/submission_log.json`

```json
{
  "campaign_id": "...",
  "campaign_status": "ongoing|closed",
  "packs": [
    {
      "angle_id": "...",
      "platform": "...",
      "market": "...",
      "posted_at": "<ISO8601>",
      "posted_by_account": "<account_slug>",
      "submitted_whop_at": "<ISO8601>",
      "submission_within_1h": true|false,
      "views_1h": N,
      "views_24h": N,
      "payout_expected": "<float or null>",
      "payout_observed": "<float or null>",
      "payout_flag": "low|ok",
      "suggested_flags": ["submission_late|low_payout|low_views|..."],
      "items_closed": [...],
      "items_pending": [...]
    }
  ],
  "cumulative": {
    "packs_count": N,
    "eligible_for_learning_weight": false,  // true si >= 50
    "aggregate_cpm": <float or null>
  },
  "log_event": [
    {"at": "<ISO8601>", "event": "pack_posted|submission_done|view_check|campaign_closed|...", "angle_id": "..."}
  ]
}
```

### À la fermeture de campagne (Warsmith déclare "fin") :

- Écrit dans `ARCHIVUM/learnings/learnings.json` (agrégé cumulatif — préserve les campagnes précédentes)
- Marque `campaign_status: "closed"` dans IW_CUSTOS + liber_clipping.json
- Génère `OUT/campaign_summary.md` — synthèse lisible de ce que la campagne a rapporté
- Déclenche une réarme possible : le Warsmith peut lancer la campagne suivante (avec archivage/effacement de `ARCHIVUM/campaign/`)

---

## MÉCANIQUE LEARNINGS — BOUCLÉE

### Seuil de pondération
- **`learnings.json` cumul < 50 packs exécutés** : poids nul. ANGLESMITH ne pondère pas les angles (tous égaux, neutres).
- **>= 50 packs cumulés** : activation progressive. Les angles avec meilleur CPM réel remontent dans la pondération ; les perdants descendent.

### Structure learnings.json

```json
{
  "cumulative_packs_executed": N,
  "eligible_for_weighting": false,  // <- true si N >= 50
  "angle_performance": [
    {
      "angle_family": "...",
      "emotion_mode": "...",
      "engagement_type": "...",
      "reframe_dim": "...",
      "platform": "...",
      "market": "...",
      "packs_count": N,
      "mean_views_24h": N,
      "mean_payout": N,
      "weight": 1.0   // 1.0 = neutre. augmente/diminue progressivement 
                      // quand eligible_for_weighting = true
    }
  ],
  "campaign_history": [
    {"campaign_id": "...", "closed_at": "<ISO8601>", "packs_count": N, "total_payout": N}
  ]
}
```

ANGLESMITH lit `angle_performance[*].weight` pour pondérer le sélection d'angles.

---

## PATTERN D'EXÉCUTION

F06 ne fait pas appel à l'IRON ni au modèle premium. C'est une frégate purement déterministe qui:
- Met à jour `submission_log.json` sur saisies Warsmith
- Calcule des agrégats (CPM, poids)
- Ferme la campagne sur déclaration Warsmith

```
python tracker.py --post --angle <angle_id> --account <slug>   # Marque "posté"
python tracker.py --submit --angle <angle_id>                # Marque "soumis Whop"
python tracker.py --views --angle <angle_id> --1h N --24h N  # Enregistre vues
python tracker.py --payout --angle <angle_id> --amount N     # Enregistre payout
python tracker.py --close-campaign                           # Ferme + agrège learnings
```

---

## CONTRATS RÉFÉRENCÉS

- `ARCHIVUM/rules/whop_rules.md` — deadline soumission 1h
- `ARCHIVUM/rules/clipping_rules.md` — seuil low payout
- `ARCHIVUM/channels/<account>/performance.json` — mis à jour avec chaque pack posté

---

## DÉPENDANCES

- **Amont** : F05_PACKAGER (production packs avec submission_checklist imbriquée), Warsmith (saisies de vues/payouts)
- **Downstream** :
  - `ARCHIVUM/learnings/learnings.json` (nourri)
  - ANGLESMITH (lit les poids pour pondération — se déclenche seulement à partir de 50 packs cumulés)
  - IW_CUSTOS.py (statut campagne = closed sur action Warsmith)

---

## HÉRÉSIES

- ❌ Auto-poster ou auto-submit (l'opérateur poste ; F06 logge seulement)
- ❌ Invoquer l'IRON ou le premium (c'est pur mécanique de log + calcul)
- ❌ Activer la pondération avant 50 packs cumulés
- ❌ Omettre la fermeture de campagne (sans `--close-campaign`, la campaign/ reste "ongoing" et F00_CAPTEURS continue à scraper — ce qui n'est pas désiré)

---

## STATUT

| Phase | État | Notes |
|---|---|---|
| Arborescence créée | ✅ | |
| TRACKING.md rédigé | ✅ | Ce fichier |
| Code Python implémenté | ✅ | v1 — commit bdd7014 (tests mock TEST_F06) |
| `tracker.py` | ✅ | CLI multi-commandes (post/submit/views/payout/close-campaign) |
| `libs/learnings_aggregator.py` | ✅ | Agrégation par clé composite 6 axes, weight progressif clampé [0.5, 2.0] au-delà de 50 packs, historique préservé |
| `libs/channel_performance_updater.py` | ✅ | `ARCHIVUM/channels/<slug>/performance.json` (packs + totaux) |
| `libs/readings_validator.py` | ✅ | Cohérence saisies Warsmith (monotonie, doublons, négatifs refusés) |
| `requirements_c06.txt` | ✅ | Standard lib Python (json, datetime, re) — pas de SDK premium |
| `IW_CUSTOS.py` | ✅ (étendu) | Nouveau mode `--mode close-campaign` (campaign_status closed + siege_closed_at) |

### Décisions v1 (résumé)
- Axes d'angle copiés du pack F05 vers l'entrée du submission_log au `--post` (l'agrégation learnings en a besoin).
- Seuils low_payout / low_views lus par regex dans clipping_rules.md — défaut 0 si non déclarés (flag inactif, jamais de faux positif).
- `submission_within_1h` vs `deadline_min` du checklist (60 min par défaut) ; flag `submission_late` si dépassé.
- Poids v1 : neutres (1.0) tant que cumulative < 50 ; activation progressive ensuite. Le flag `eligible_for_weighting` est la source de vérité lue par ANGLESMITH.
- `--close-campaign` : learnings préservés (append/update) + aggregate_cpm + campaign_summary.md + check-in F06 (→ campaign_closed) + close-campaign IW_CUSTOS.

*Fer au-dedans, Fer au-dehors. Le siège est fini quand le tracker a fermé le ledger.*
