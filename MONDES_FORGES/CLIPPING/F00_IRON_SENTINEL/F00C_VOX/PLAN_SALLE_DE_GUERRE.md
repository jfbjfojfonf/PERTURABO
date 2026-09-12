# PLAN_SALLE_DE_GUERRE — Correctif F00C + Le Prince Voit Tout

> **Statut : ✅ COMPLET — Livraisons A + B + C + D livrées (escalier anti-bot, barre rouge + webhook, dashboard Salle de Guerre, mode LIVE + gate cockpit).
> Reste : le run réel Sophie Rain (secret `YT_COOKIES_BASE64` côté Warsmith).**
> Document de référence avant toute ligne de code. Ne rien modifier ici sans revalidation du Warsmith.
> Prédécesseurs : `PLAN_REFONTE_VOX.md` (F00B, ✅), Note 20 (pont PUR F00C, ✅).

**Date** : 2026-09-12 · **Branche** : `v2-live-vox-c` · **Campagne de test** : Sophie Rain (`us_young_english`)

---

## 1. Principe structurant — la doctrine en une phrase

**« Le Primarque voit tous les points d'intérêt depuis son siège — ce qui lui garantit une victoire totale. »**

Concrètement, deux chantiers indissociables :

1. **Le correctif du siège (F00C, Python)** — le runner GitHub doit VRAIMENT obtenir le média, produire heatmap + segments + candidats, et ne plus jamais afficher de faux vert.
2. **La Salle de Guerre (workspace Freebuff, Vite + React + Convex)** — le Warsmith VOIT les données brutes et les candidats en temps réel dans sa preview, sans jamais télécharger un artifact à la main. Gate Warsmith transformée en cockpit : boutons GO / NO-GO sur chaque carte.

**Rappel des rôles (gravé)** : F00B = Twitch exclusivement. F00C = YouTube/local. Tout le travail de la campagne Sophie Rain touche **F00C uniquement**. F00B n'apparaît ici que comme héritage de contrats (`candidats.json`) et pour le mode LIVE (flux chat → timeline).

---

## 2. Architecture globale

```
┌────────────────────────────────────────────────────────────────────┐
│ REPO PERTURABO (Python, GH Actions)      WORKSPACE FREEBUFF        │
│                                          (kbkjhjhl — Vite+Convex)  │
│ F00C_VOX ──analyse──► manifeste + heatmap + candidats.json         │
│    │                                                               │
│    └──webhook HTTPS (X-Siege-Token)──► CONVEX (backend réactif)    │
│                                          ▲              │          │
│ F00B live ──webhook (chat/candidats)─────┘              ▼          │
│ (mode LIVE)                          SALLE DE GUERRE /war-room     │
│                                      ← le Warsmith, en preview     │
└────────────────────────────────────────────────────────────────────┘
```

- Le webhook Convex est **unidirectionnel** (PERTURABO → Salle de Guerre). Aucune donnée média ne remonte vers le repo.
- Convex = souscriptions réactives : dès qu'un run GitHub pousse, la preview change toute seule.
- Le média vidéo (Sophie Rain = contenu sous copyright) ne vit **jamais** ni dans le repo ni dans Convex. Seules les **données d'analyse** (timestamps, scores, courbes) sont stockées.

---

## 3. Les livraisons (phases, responsables, fichiers touchés)

### Livraison A — Le siège débloqué (correctif F00C)

| # | Quoi | Qui | Fichiers |
|---|---|---|---|
| 0 | **Test gratuit** `--extractor-args "youtube:player_client=ios,mweb"` en premier essai avant cookies (l'ère des PO tokens le fait souvent échouer — c'est un test, pas une fondation) | Moi | `f00c_vox.py` |
| 1 | **Garde-fou anti-faux-vert** : exit 1 + message explicite si `download_budget_seconds > 0` et `status != "full"`, ou si `to_candidats` avec 0 candidat | Moi | `f00c_vox.py` + workflow |
| 2 | **Contrat découplé** `--media-source` (URL/fichier média séparé de l'URL YouTube qui garde les métadonnées) | Moi | `f00c_vox.py` + workflow + docs F00C |
| 3 | **Cookies burner** : secret `YT_COOKIES_BASE64` → décodage dans fichier temporaire (`umask 077`) → `yt-dlp --cookies` → destruction en fin de job | Warsmith crée le burner + le secret / moi le code | workflow |
| 4 | **Téléchargement 144p video-only** (la heatmap réduit à 64×36 ; ~30-60 Mo/h au lieu de Go) | Moi | `f00c_vox.py` |

**Côté Warsmith — récupération des « cookies » (ce ne sont pas un token API)** :
1. Compte Google **burner** (jamais le compte de publication), profil navigateur dédié
2. Connexion YouTube avec ce compte → extension « Get cookies.txt LOCALLY » → export Netscape de `youtube.com`
3. Encodage local : `base64 -w0 cookies.txt`
4. GitHub → repo → **Settings → Secrets and variables → Actions → New repository secret** → nom `YT_COOKIES_BASE64` → coller → Save
5. Rotation hebdomadaire (checklist du lundi). Révocation immédiate si alerte Google. **Jamais collé dans le chat, un commit ou un workflow log.**

### Livraison B — La barre rouge + le pont

| # | Quoi | Qui | Fichiers |
|---|---|---|---|
| 5 | **Most Replayed** : la heatmap comportementale YouTube (points `start_time/end_time/value` exposés par yt-dlp) récupérée avec les cookies, fusionnée avec la heatmap vidéo → c'est le croisement le plus puissant du projet (ton capteur × des millions d'humains réels) | Moi | `f00c_vox.py` |
| 6 | **Webhook Convex v1** : POST du manifeste + candidats + courbes, auth `X-Siege-Token` (secret partagé), idempotent par `run_id` — **dans le repo Salle de Guerre (`kbkjhjhl`) + script d'envoi webhook dans PERTURABO** | Moi | `convex/http.ts`, `f00c_vox.py` (`--webhook-url`) |

### Livraison C — La Salle de Guerre (mode VOD)

| # | Quoi | Qui |
|---|---|---|
| 7 | Schéma Convex : tables `sieges`, `candidats`, `heatmap`, `replayed_curve`, `events` — **repo Salle de Guerre** | Moi |
| 8 | Dashboard `/war-room` (protégé auth, thème Iron Warriors) : **timeline maîtresse** (heatmap vidéo en aire + barre rouge Most Replayed superposée + marqueurs pics + blocs candidats), clic bloc → détail (score, décomposition critères, timestamps, plateformes), **toggle DONNÉES BRUTES** affichant les JSON complets — **repo Salle de Guerre** | Moi |
| 9 | Mode **VOD** : tout arrive d'un coup → tous les clips enfilés triés par score, rétrospective de siège — **repo Salle de Guerre** | Moi |

### Livraison D — Mode LIVE + cockpit de gate

| # | Quoi | Qui |
|---|---|---|
| 10 | Mode **LIVE** : candidats poussés au fil de l'eau → cartes qui apparaissent en temps réel + marqueur pulsant sur la timeline | Moi |
| 11 | **Gate Warsmith inline** : boutons GO / NO-GO sur chaque carte, verdict renvoyé dans le pipeline (le Warsmith commande, il ne détecte plus) | Moi + endpoint Convex `gate` |

---

## 4. Contrat du webhook (schéma canonique)

```json
{
  "run_id": "gh_run_1234567",
  "siege_id": "SOPHIE_RAIN_CLIPIFY_2026-09",
  "mode": "vod | live",
  "status": "full | metadata_only",
  "source": {"url": "...", "type": "youtube_vod | youtube_live | twitch_vod | local"},
  "heatmap": [{"t": 0, "value": 0.12}],
  "replayed_curve": [{"start": 0, "end": 20, "value": 0.9}],
  "candidates": [{"id": "clip_01", "rank": 1, "start": 72.5, "end": 107.2,
                  "score": 94.8, "criteria": {"hook": 0.9, "emotion": 0.88},
                  "platforms": ["youtube_shorts", "tiktok", "instagram_reels", "x"],
                  "gate": "pending"}],
  "pushed_at": "2026-09-12T10:42:00Z"
}
```

Règles : `X-Siege-Token` obligatoire (sinon 401) ; re-POST du même `run_id` = idempotent ; `status: metadata_only` en mode VOD = rejeté côté webhook aussi (double garde-fou).

---

## 5. Sécurité (résumé des décisions)

| Actif | Protection |
|---|---|
| Comptes de publication | Ne touchent jamais yt-dlp — silos étanches (le burner télécharge, l'opérateur publie) |
| IP résidentielle du Warsmith | Aucune requête de download depuis son PC ; risque porté à 100 % par le compte burner |
| Cookies | Secret GitHub + fichier temporaire détruit en fin de job + rotation hebdo |
| Webhook Convex | `X-Siege-Token` secret partagé — pas d'injection possible |
| Média copyright | Jamais dans le repo public ni Convex — runner éphémère uniquement |
| Piste 5 (runner self-hosted) | Écartée — exposerait l'IP résidentielle |

---

## 6. Phase DOCS — mise à jour obligatoire (livrée avec chaque livraison)

Aucune livraison n'est « terminée » tant que la docs ne suit pas. À chaque livraison :

| Livraison | Docs à mettre à jour |
|---|---|
| A | Guide `19_MODE_VOX_C_YOUTUBE.md` (+ nouvelle note technique garde-fou/cookies), `TRACKING/F00C_LOG.md` (Note : Livraison A), `CONTINUATION_F00.md` (section « Ajouté ») |
| B | Même trio + `20_NOTE_TECHNIQUE_PUR_BRIDGE_F00C.md` (contrat webhook) |
| C | Nouveau guide `21_SALLE_DE_GUERRE.md` (mode VOD : lecture timeline, gate, données brutes), `README_V2.md` (table F00 → + Salle de Guerre), trio TRACKING/CONTINUATION |
| D | Guide 21 (mode LIVE + cockpit), trio TRACKING/CONTINUATION, `_PIEGES_APPRIS_PUR.md` si nouveau piège rencontré |

**CONTINUATION_F00.md** est le fichier de reprise « à froid » : sa section « Dernière mise à jour » doit toujours refléter la dernière livraison poussée.

---

## 7. Protocole COMMIT / PUSH — LES DEUX REPOS, TOUT CE QUI EST PRODUIT

> **Règle absolue : RIEN n'est terminé tant que ce n'est pas commité ET poussé.**
> Une livraison "finie dans le workspace" n'existe pas — si elle n'est pas sur GitHub,
> elle sera perdue au prochain reset. Chaque livraison se termine par un push vérifié.

### 7.1 Les deux repos de ce plan

| Repo | Contenu | Branche | Ce qui y est commité |
|---|---|---|---|
| **PERTURABO** (`jfbjfojfonf/PERTURABO`) | Python F00C + workflow GH + guides + tracking | `v2-live-vox-c` | `f00c_vox.py`, tests, workflow YAML, guides, `F00C_LOG.md`, `CONTINUATION_F00.md` |
| **Salle de Guerre** (`tresa5932-cmd/kbkjhjhl`, workspace Freebuff connecté) | Dashboard Vite+React+Convex | `main` | schéma Convex, `http.ts` (webhook), composants `/war-room`, tests, README/CHANGELOG interne |

### 7.2 Checklist de fin de livraison (OBLIGATOIRE, dans l'ordre)

1. **Vérification** : `python3 -m py_compile` sur tout `.py` touché · `bun tsc -b --noEmit` (repo Salle de Guerre) · tests verts · relecture `git diff --stat`.
2. **Docs à jour** (section 6) — le commit de code NE part JAMAIS sans ses docs.
3. **PERTURABO** : `git add` explicite des fichiers de la livraison (jamais `git add .` aveugle) → commit (format repo) → `git push origin v2-live-vox-c` → **vérifier la sortie du push** (doit finir sans erreur) → `git log origin/v2-live-vox-c -1` pour confirmer.
4. **Salle de Guerre** (si la livraison y touche) : même protocole sur `main` → `git push origin main` → vérification identique.
5. **Rapport au Warsmith** : SHA des commits, fichiers inclus, résultat du push (réussi ou bloqué). Un push bloqué (403) n'est **jamais contourné** (pas de PAT, pas d'API REST) : il est signalé et le Warsmith reconnecte le repo — le commit attend local, prêt à repartir.
6. **Un commit par livraison, jamais un méga-commit.** Si une livraison touche les deux repos : deux commits (un par repo), rapportés ensemble.

### 7.3 Hygiène

- Jamais de force-push, jamais de reset destructive, jamais d'historique réécrit.
- Secrets, cookies, tokens : **jamais** dans un commit, un log ou le chat.
- Fichiers média (copyright) : jamais commités — uniquement les données d'analyse (JSON/CSV de courbes et scores).

---

## 8. Test de siège Sophie Rain — critères de réussite

Relance du même workflow que le run raté, attendu :

- [ ] `status: full` (pas `metadata_only`) — sinon le job **échoue** (garde-fou)
- [ ] Heatmap complète (nb buckets demandés) + barre rouge Most Replayed récupérée
- [ ] ≥ 3 segments viraux et ≥ 3 candidats dans `candidats.json`
- [ ] Pont PUR émis (Note 20) — candidats visibles dans la Salle de Guerre `/war-room`
- [ ] Gate GO / NO-GO fonctionnelle depuis la preview
- [ ] Logs TRACKING + CONTINUATION mis à jour dans le commit de livraison

---

## 9. Backlog — hors périmètre maintenant (issu du brainstorm du 2026-09-12)

- Hook words + pics WPM si transcription disponible (nécessite Whisper/pipeline F00B)
- Seamless loop (Open Loop Neurologique) + hook frame-0 dans `ARCHIVUM/montage/` et F06_DIRECTOR
- Learnings post-publication : connecter les stats des posts au scoring (déjà prévu par la doctrine learnings)
- **Refusés définitivement** : Ragebait Index (viole la directive : pas de bait/misinfo/PR négative), scramble d'empreinte audio (contenu autorisé Whop → fingerprint non applicable, et risque de détection de manipulation)

---

* forge, analyse, siège. ⚒️
