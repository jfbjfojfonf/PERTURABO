# 14 — Guide Opérateur : Mode PUR

> Ce guide est pour **l'opérateur** (le Warsmith) qui lance un siège PUR.
> Pas besoin de connaître le code. Suivez les étapes.

---

## Checklist rapide

- [ ] URLs VODs Twitch prêtes
- [ ] Nombre de clips voulu décidé
- [ ] Directive campagne chargée (ou template rempli)
- [ ] Watermark PNG du créateur dans `watermarks/`
- [ ] yt-dlp + ffmpeg installés (pour ingest réel)

---

## Étape 1 — Préparer l'input

Créez `IN/vox_input.json` :

```json
{
  "vod_urls": [
    {"url": "https://www.twitch.tv/videos/1234567890", "alias": "stream_01"}
  ],
  "segments": [
    {"alias": "stream_01", "start": "02:14:20", "end": "02:15:00", "id": "seg_01"},
    {"alias": "stream_01", "start": "03:45:10", "end": "03:46:30", "id": "seg_02"}
  ],
  "nb_clips_demandes": 4,
  "budget_max_sec": 1200
}
```

**Règle :** Budget max 20 min par session. Ne téléchargez JAMAIS la VOD complète.

---

## Étape 2 — Ingest

```bash
python F00B_VOX/CODEBASE/f00b_vox.py ingest
```

Ça génère `OUT/vox_manifest.json` avec les commandes yt-dlp.

Pour exécuter (téléchargement réel) :
```bash
python F00B_VOX/CODEBASE/f00b_vox.py ingest --execute
```

---

## Étape 3 — Signaux (optionnel)

Si vous avez des timestamps de moments forts, créez `IN/signals.json` :

```json
{
  "signals": [
    {"start": "02:14:25", "end": "02:14:45", "type": "chat_spike", "intensity": 0.9}
  ]
}
```

Types : `chat_spike`, `energy`, `trigger_word`, `punchline`
Intensité : 0.0 (faible) → 1.0 (très fort)

---

## Étape 4 — Détection + Scoring

```bash
python F00B_VOX/CODEBASE/f00b_vox.py detect
python F00B_VOX/CODEBASE/f00b_vox.py score
```

Ça produit `OUT/candidats.json` et `OUT/scoring.json`.

---

## Étape 5 — Gate (VOTRE VALIDATION)

```bash
python F00B_VOX/CODEBASE/f00b_vox.py gate
```

Ouvrez `OUT/gate_verdict.json`. Pour chaque candidat :
- `pending_warsmith` → Vous devez décider
- Changez en `"approved"` ou `"rejected"`
- Ajoutez un `"motif"` si rejeté

Exemple :
```json
{"candidate_id": "abc123", "status": "approved"}
{"candidate_id": "def456", "status": "rejected", "motif": "pas assez percutant"}
```

Puis :
```bash
python F00B_VOX/CODEBASE/f00b_vox.py gate_apply
```

---

## Étape 6 — Trail final

```bash
python F00B_VOX/CODEBASE/f00b_vox.py trail
```

`OUT/trail.json` contient les segments prêts pour F03_SOURCE_HUNTER.

---

## Étape 7 — Campagne (si applicable)

Si vous avez une directive campagne :

```bash
python ARCHIVUM/campaign/campaign_directive_parser.py \
  ARCHIVUM/campaign/ma_directive.md \
  -o ARCHIVUM/campaign/campaign_directive.json
```

Le JSON produit contient :
- Payouts par plateforme
- Règles caption/tagging
- Règles watermark
- Règles anti-spam

---

## Étape 8 — Poster

1. Lancez F03 → F04 → F05 → F06
2. Récupérez le production pack (clips + watermark + captions)
3. Postez sur les plateformes selon les règles de la campagne
4. Soumettez à Whop dans les délais

---

## Règles d'or

| Règle | Pourquoi |
|-------|----------|
| Jamais de VOD complète | Budget + légal |
| Jamais de recompression | Stream copy uniquement |
| Jamais de trail sans gate | Le Warsmith décide |
| Watermark ≥ 75% | Exigence campagne |
| Pas de CTA | Contenu organique |
| Anti-detection obligatoire | Éviter la suppression |

---

## Commandes rapides

```bash
# Pipeline complet (7 étapes)
python F00B_VOX/CODEBASE/f00b_vox.py ingest
python F00B_VOX/CODEBASE/f00b_vox.py detect
python F00B_VOX/CODEBASE/f00b_vox.py score
python F00B_VOX/CODEBASE/f00b_vox.py gate
# → éditer gate_verdict.json →
python F00B_VOX/CODEBASE/f00b_vox.py gate_apply
python F00B_VOX/CODEBASE/f00b_vox.py trail

# Vérifier l'état
python F00B_VOX/CODEBASE/f00b_vox.py status

# Parser une directive campagne
python ARCHIVUM/campaign/campaign_directive_parser.py directive.md
```

---

*Fer au-dedans, Fer au-dehors. Le siège continue.* 🔩
