# PERTURABO — Reverse Engineering YouTube

> *"Fer au-dedans, Fer au-dehors."*
> — IV Légion, Iron Warriors

```
[░░░░░░░░░░░░░░░░] STRUCTURE ARCHITECTURALE VALIDÉE — SIEGE ENGINE INITIALISÉ
Phase active    : GREFFE DOCTRINALE — RUBICON PRIMARIS
Cible           : Territoire YouTube (Mode Vidéo + Mode Chaîne)
Coût            : 0.00 EUR (stack 100% open-source, hors API OpenAI)
Lien écosystème : SANCTORUM (pipeline audio), DORN (pipeline visuel)
```

---

## Présentation

PERTURABO est un organisme de **reverse engineering YouTube** construit selon la doctrine
de la **Media Pipeline Architecture**. Il analyse les vidéos virales, extrait leur squelette
caché, et produit des scripts + miniatures + stratégies de niche pour le territoire YouTube.

Nommé en l'honneur de **Perturabo**, Primarch de la IV Légion — les Iron Warriors — dont la
capacité d'analyse pouvait voir chaque faille d'une fortification avant le premier coup.

L'analyse précède le siège. La compréhension précède la production.

---

## Architecture — Les Frégates

| Frégate | Nom de Code | Analogie | Rôle |
|---|---|---|---|
| F01 | SENTINEL | La Reconnaissance de Fer | Capture le specimen (OSINT : transcription + métadonnées) |
| F02 | BREACHER | Le Briseur de Murs | Extrait le squelette viral du specimen |
| F03 | FORGEWARD | La Forge de Fer | Génère le script complet pour la nouvelle niche |
| F04 | HERALD | Le Porte-Étendard | Analyse + génère le concept miniature (Visual Skeleton → Midjourney) |
| F05 | GRAND COMPASS | Le Compas | Niche bending + validation océan bleu |
| TYRANT | LE TYRANT | L'Oracle (Psyker II) | Vision stratégique pré-siège |
| ORCH | L'ORCHESTRATEUR | Le Nerf Central | Coordination du flux entre les portes |
| CAPT | LES CAPTEURS | Le Fer qui Veille | Surveillance continue des concurrents |

**Principe d'étanchéité :** chaque frégate opère dans son silo `IN/ → CODEBASE/ → OUT/`.
La seule communication inter-frégates passe par `liber_perturabo.json` via `IW_CUSTOS.py`.

---

## Structure du Dépôt

```
PERTURABO/
├── README.md
├── IW_CUSTOS.py                          ← Gardien de la flotte (check-out/check-in/validate/status)
├── liber_perturabo.json                  ← CMS centralisé — seul vecteur inter-frégates
├── RUBICON.md                            ← Plan de transfiguration
├── VERBUM.md                             ← Document fondateur (doctrine)
│
├── CONTRACTS/                            ← Contrats de l'IA
│   ├── system_prompt.md                  ← Doctrine complète (muté)
│   ├── tyrant_prompt.md                  ← Contrat spécifique du TYRANT
│   ├── iron_prompt.md                    ← Contrat spécifique de l'IRON
│   ├── skeleton_checklist.json           ← Checklist d'extraction du squelette viral
│   └── anti_bullshit.md                  ← Filtre anti-fausses règles d'or
│
├── ARCHIVUM/                             ← La Mémoire Impériale (fondation)
│   ├── transcripts/                      ← Transcriptions capturées par les Capteurs
│   ├── rules/                            ← Règles d'or extraites et validées
│   ├── templates/                        ← Artefacts produits (scripts générés)
│   └── ledgers/                          ← Grand Company Ledgers (un par siège)
│
├── TRACKING/
│   ├── IW_CAMPAIGN_LOG.md                ← Log général de campagne
│   └── IW_TRANSFER_LOG.md                ← Log des transferts inter-frégates
│
├── CAPTEURS/
│   ├── IN/                               ← URLs des chaînes à surveiller
│   ├── OUT/                              ← Signaux capturés (JSON)
│   ├── TRACKING/
│   │   └── CAPT_LOG.md
│   └── CODEBASE/
│       ├── iron_sentinel.py              ← Surveillance continue des concurrents
│       ├── pattern_capture.py            ← Capture et catalogage des patterns
│       └── alert_system.py               ← Alerte le TYRANT sur signaux
│
├── F01_SENTINEL/
│   ├── IN/                               ← URL YouTube (fournie par le Warsmith)
│   ├── OUT/                              ← transcript.json + metadata.json
│   ├── TRACKING/
│   │   └── F01_LOG.md
│   └── CODEBASE/
│       ├── sentinel.py                   ← Récupération OSINT (yt-dlp + youtube-transcript-api)
│       └── requirements_f01.txt
│
├── F02_BREACHER/
│   ├── IN/                               ← transcript.json (de F01)
│   ├── OUT/                              ← skeleton.json
│   ├── TRACKING/
│   │   └── F02_LOG.md
│   └── CODEBASE/
│       ├── breacher.py                   ← Extraction du squelette viral
│       └── requirements_f02.txt
│
├── F03_FORGEWARD/
│   ├── IN/                               ← skeleton.json (de F02) + niche
│   ├── OUT/                              ← script.json + metadata.json
│   ├── TRACKING/
│   │   └── F03_LOG.md
│   └── CODEBASE/
│       ├── forgeward.py                  ← Génération du script
│       └── requirements_f03.txt
│
├── F04_HERALD/
│   ├── IN/                               ← thumbnail_url + titre (de F03) + niche
│   ├── OUT/                              ← thumbnail_concept.json
│   ├── TRACKING/
│   │   └── F04_LOG.md
│   └── CODEBASE/
│       ├── herald.py                     ← Analyse visuelle + prompt Midjourney
│       └── requirements_f04.txt
│
├── F05_GRAND_COMPASS/
│   ├── IN/                               ← transcript.json (de F01) + recherche web
│   ├── OUT/                              ← niche_report.json
│   ├── TRACKING/
│   │   └── F05_LOG.md
│   └── CODEBASE/
│       ├── grand_compass.py              ← Niche bending + validation océan bleu
│       └── requirements_f05.txt
│
├── TYRANT/
│   ├── IN/                               ← Brief du Warsmith + signaux des Capteurs
│   ├── OUT/                              ← Rapport d'Éclairement (JSON)
│   ├── TRACKING/
│   │   └── TYRANT_LOG.md
│   └── CODEBASE/
│       ├── tyrant.py                     ← Vision stratégique pré-siège
│       └── requirements_tyrant.txt
│
├── ORCHESTRATOR/
│   └── CODEBASE/
│       ├── orchestrator.py               ← Nerf central — flux entre les portes
│       └── gates.py                      ← Logique des 4 portes de siège
│
├── SHARED/
│   ├── IN/
│   └── OUT/                              ← Artefact final (script + miniature + métadonnées)
│
└── .github/workflows/
    └── iron_sentinel.yml                 ← Capteurs automatisés (surveillance continue)
```

---

## Les Quatre Portes de Siège

| Porte | Moment | Ce que le Warsmith fait |
|---|---|---|
| Porte 1 | Avant le siège | Fournit URL + niche. Le TYRANT éclaire le territoire. |
| Porte 2 | Après BREACHER | Valide ou rejette le squelette viral extrait. |
| Porte 3 | Après FORGEWARD | Valide ou demande révision du script généré. |
| Porte 4 | Après artefact complet | Valide la publication ou archive. |

Entre les portes, l'IRON travaille. Le Warsmith ne touche pas au code.

---

## Axiomes Impériaux

| # | Axiome | Loi |
|---|---|---|
| I | Coût Zéro | Stack 100% open-source (hors API OpenAI) |
| II | Isolation Absolue | Zéro appel direct entre frégates — tout passe par `liber_perturabo.json` |
| III | Étanchéité des Silos | Chaque frégate : `IN/ → CODEBASE/ → OUT/` — pas de fuite |
| IV | Le Gardien Veille | `IW_CUSTOS.py` est le seul autorisé à modifier `fleet_status` |
| V | Le Ledger Voyage | Le Grand Company Ledger reconstitue le contexte si le sandbox brûle |
| VI | Le Fer qui Veille | Les Capteurs ne dorment jamais — surveillance continue |
| VII | L'Analyse Précède | Le TYRANT voit avant que les frégates ne tournent |

---

## Stack Technologique

| Composant | Bibliothèque | Frégate |
|---|---|---|
| Transcription | youtube-transcript-api | F01 |
| Métadonnées | yt-dlp | F01 |
| Recherche web | DuckDuckGo (requests) | F05, CAPTEURS |
| IA Vision (miniature) | OpenAI GPT-4o Vision | F04 |
| IA (squelette + script) | OpenAI GPT-4o | F02, F03 |
| IA stratégique (Oracle) | OpenAI GPT-4o | TYRANT |
| Communication | liber_perturabo.json via IW_CUSTOS.py | Toutes |
| Stockage | GitHub | Toutes |
| Automatisation | GitHub Actions | CAPTEURS |

---

## Déploiement Rapide

```bash
git clone <repo-url>
cd PERTURABO
pip install -r F01_SENTINEL/CODEBASE/requirements_f01.txt
# ... (une frégate à la fois, ou requirements global)

# Vérifier l'état de la flotte
python IW_CUSTOS.py --mode status

# Lancer un siège (via l'Orchestrateur)
python ORCHESTRATOR/CODEBASE/orchestrator.py --mode video --url "https://youtube.com/watch?v=XXXX" --niche "Le Seigneur des Anneaux"
```

---

## Lien avec SANCTORUM et DORN

PERTURABO produit les **scripts et stratégies**. SANCTORUM produit l'**audio**.
DORN produit le **visuel**. Les trois forment un écosystème complet :

```
PERTURABO (script + stratégie) → SANCTORUM (audio) → DORN (visuel) → Publication
```

---

*IV Légion — Iron Warriors*
*Que le siège commence.*
