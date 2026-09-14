# ARCHIVUM/campaign/ — LA campagne en cours (singulier)

> *Une seule campagne à la fois. Quand on en finit une, on archive ou on efface, et on repart vierge.*
> *Chaque campagne est un cas isolé — pas de mémoire comparative en parallèle.*

---

## Pourquoi singulier ?

Chaque campagne Whop est différente : assets différents, niche différente, mécène différent. La mémoire comparative n'a pas de valeur sur des unités non-comparables. La campagne en cours reste seule, isolée, comme une forteresse sous siège.

## Fichiers attendus (au runtime)

| Fichier | Rôle | Qui l'écrit | Quand |
|---|---|---|---|
| `directive.md` | Goal doc Whop tel quel | Warsmith | Avant Porte 1 |
| `reference_clip.json` | URL + métriques du clip gagnant | Warsmith | Avant Porte 1 |
| `reference_skeleton.json` | Squelette viral extrait (pourquoi marché) | F01_SCOUT → F02 | Porte 1 |
| `verdict.json` | Éclairement TYRANT (GO/NO-GO + blue_ocean) | F02_TYRANT_CAMP | Porte 1 |

## Cycle de vie

1. **Init siège** : Warsmith dépose `directive.md` + `reference_clip.json`
2. **Siège actif** : F01 → F02 écrivent `reference_skeleton.json` + `verdict.json`
3. **Siège en cours** : `directive.md` est lu par toutes les frégates (assets source)
4. **Fermeture** : Warsmith déclare `--close-campaign` → F06 agrège learnings
5. **Reset** : Le Warsmith archive (déplace vers un dossier extern) ou efface les 4 fichiers, et repart vierge pour la campaigne suivante.

## Note d'archivage

L'archivage des campagnes passées n'est pas géré par le forge lui-même — c'est une opération manuelle du Warsmith. Si tu veux garder l'historique, déplace `campaign/` vers un dossier externe type `ARCHIVES/<campaign_id>/`. Le forge ne garde que la campagne **active**.

## Hist passed campaigns dans `learnings/`

Les résultats d'une campaigne close sont **agrégés** dans `ARCHIVUM/learnings/learnings.json` (champ `campaign_history`). Donc la mémoire n'est pas perdue même quand on efface `campaign/`.
