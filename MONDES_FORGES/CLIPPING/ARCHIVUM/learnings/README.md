# ARCHIVUM/learnings/ — Boucle rétro-active

> *Mémoire cumulée des perf réelles par angle. Nourrit ANGLESMITH pour pondération progressive.*

---

## Fichier attendu

### `learnings.json`

```json
{
  "cumulative_packs_executed": 0,
  "eligible_for_weighting": false,
  "angle_performance": [],
  "campaign_history": []
}
```

## Mécanique

### Seuil de pondération
- `cumulative_packs_executed < 50` : `eligible_for_weighting = false`. ANGLESMITH ne pondère pas — tous les angles sont neutral (weight = 1.0).
- `cumulative_packs_executed >= 50` : `eligible_for_weighting = true`. ANGLESMITH lit les `weight` et pondère les angles (gagnants montent, perdants descendent).

### Structure de `angle_performance[]`

```json
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
  "weight": 1.0
}
```

`weight` commence à 1.0 (neutre). Au fil du temps (> 50 packs), augmente/diminue selon la perf relative de l'angle vs médiane.

### Structure de `campaign_history[]`

```json
{
  "campaign_id": "...",
  "closed_at": "<ISO8601>",
  "packs_count": N,
  "total_payout": N
}
```

## Mise à jour

- Nourri par F06_TRACKER à chaque fermeture de campaigne (`--close-campaign`)
- Lu par ANGLESMITH à la Porte 2 pour pondérer les angles forgés

## Statut initial

`squelette.json` présent pour servir de démarrage. F06_TRACKER doit le charger au premier siège, l'enrichir, le sauvegarder.
