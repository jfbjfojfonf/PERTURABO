# Guide du mode STAND UP — LACRIMAE

**Branche de référence :** `dev3`
**Mode parent :** `MEME`
**Point d’arrêt :** F00 / Porte I
**Validation :** Oracle exécute, Champion choisit et valide

## 1. Positionnement

Le mode STAND UP est une voie éditoriale séparée du mode MEME pur. Il ne remplace pas le pipeline MEME existant et ne modifie pas le mode LOGO. Il sert à transformer un transcript fourni par le Champion en un maximum de sept sujets originaux et réutilisables.

Le mode STAND UP ne produit pas de vidéo, ne génère pas de codex de rendu et ne lance pas F01 automatiquement. Il s’arrête à F00 avec un rapport que le Champion doit examiner.

## 2. Choix initial de l’Oracle

Au début d’une production, l’Oracle demande :

```text
Mode de production : MEME ou LOGO ?
```

Lorsque `MEME` est choisi, il demande ensuite :

```text
Variante MEME : pur ou STAND UP ?
```

Les valeurs de dispatch sont :

```text
production_mode = meme | logo
meme_variant = pure | stand_up
```

`meme_variant` n’est pertinent que lorsque `production_mode=meme`.

## 3. Entrée STAND UP

L’entrée obligatoire est un transcript fourni par le Champion dans le champ `transcript`. Le workflow refuse le run si le transcript est absent ou trop court. Le texte brut n’est pas ajouté au commit de ledger ; le rapport conserve toutefois un extrait traçable et le hash SHA-256 du transcript.

Exemple de lancement :

```bash
gh workflow run lacrimae_orchestrator.yml \
  --ref dev3 \
  -f fregate=F00 \
  -f production_mode=meme \
  -f meme_variant=stand_up \
  -f title="Nouveau siège stand up" \
  -f transcript="<transcript fourni par le Champion>"
```

## 4. Traitement F00

Le script `tools/stand_up_f00.py` découpe le transcript en unités, identifie les observations exploitables, classe les mécanismes comiques, calcule un score indicatif de potentiel viral et sélectionne au maximum sept sujets.

Le rapport produit :

```text
F00_STAND_UP/OUT/stand_up_f00_report.json
F00_STAND_UP/OUT/stand_up_f00_report.md
TRACKING/STAND_UP_F00_REPORT.json
TRACKING/STAND_UP_F00_REPORT.md
```

Chaque sujet contient un `subject_id`, une observation centrale, un mécanisme comique, un score de potentiel viral, un score de réutilisabilité, un état de recherche de contexte et une décision Champion en attente.

Un score viral n’est jamais une garantie de viralité. L’originalité et la conformité exigent une revue humaine. Le système ne doit pas copier une punchline, une formulation distinctive ou la structure exacte d’un sketch tiers.

## 5. Recherche et sélection

La recherche de contexte intervient après l’extraction. Elle sert à vérifier l’actualité, la saturation du thème et les faits associés. Elle ne transforme pas automatiquement un sujet en publication. Le Champion choisit un `subject_id`; ce choix est ensuite utilisé pour préparer F01.

Un sujet peut être réutilisé dans plusieurs sièges. Chaque siège doit toutefois avoir un `siege_id`, un angle, un persona, une chute et une exécution distincts.

## 6. Porte I

À la Porte I, l’Oracle remet au Champion :

| Élément | Preuve attendue |
|---|---|
| Mode | `stand_up` |
| Transcript | Hash SHA-256 et titre, sans engagement obligatoire du texte brut |
| Sujets | 1 à 7 sujets classés |
| Originalité | Revue humaine requise |
| Viralité | Score indicatif uniquement |
| Décision | `pending` jusqu’au choix du Champion |
| Suite | Sujet choisi → F01 |

F01 ne doit être lancé qu’après le choix explicite du Champion. Le rapport STAND UP n’est pas un codex MEME et ne doit pas être envoyé directement à F02 ou F04.

## 7. Sécurité du pipeline

Le mode MEME pur doit continuer à récupérer les packs PERTURABO et à suivre son propre parcours. Le mode LOGO doit continuer à suivre le flux LOGO. Les conditions du workflow doivent empêcher F00 STAND UP de lancer l’ingestion vidéo classique et empêcher le flux classique d’interpréter un transcript STAND UP comme une vidéo source.

*Mise à jour : 2026-08-22 — Manus AI.*
