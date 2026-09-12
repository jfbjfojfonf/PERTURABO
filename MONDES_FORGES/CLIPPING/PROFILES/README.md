# PROFILES/ — Profils du forge CLIPPING

Le forge CLIPPING supporte **deux business distincts** via un système de **profil actif**. Le profil est fixé au **démarrage du siège** (IW_CUSTOS `--mode init-siege --profile whop|logo`) et écrit dans `liber_clipping.json` (champ `mode`). Tout le workflow se cale ensuite automatiquement sur ce profil. **Un siège = un seul profil** (pas de mélange mid-campaign).

## Pourquoi deux profils

- **Whop Content Rewards** : campagnes Whop, deadline 1h, FTC strict, asset imposé, pack = script complet + caption + titre. Marque paie via Content Rewards.
- **Clipping Logo** : clip de célébrité/foot/anime + **logo de marque en superposition** (casino...). Contenu libre, marque paie au **CPM** (tracker type Shortimiz). Pack = **genre + titre reframing + body + on_screen_text + seo_tags**, `n_angles` commandés.

Ce sont deux doctrines, schémas, compliance et critères de verdict différents. Le code des frégates communes (F01, F03, ANGLESMITH, F04, F05, F06, F00_CAPTEURS, IW_CUSTOS) reste **partagé** ; seul ce qui dépend du profil (CONTRACTS, F00_CAPTEURS sites, F05 schema, F04 doctrine/prompt, F02 critères) est lu via `SHARED/profile_loader.py`.

## Frontière Perturaba vs OMNIS_WATCH (inchangée dans les deux profils)

Perturaba/CLIPPING produit du **TEXTE ONLY** :
- Profil whop : script + caption + titre
- Profil logo : genre + titre reframing + body + on_screen_text + seo_tags

OMNIS_WATCH (projet externe) fait le rendu vidéo :
- Profil whop : assemble la vidéo selon le pack texte
- Profil logo : superpose le logo + affiche le on_screen_text + rend le clip final 10s

## Structure

```
PROFILES/
├── whop/
│   └── manifest.json          ← manifeste (pointe vers CONTRACTS/ à la racine, heritage)
└── logo/
    ├── manifest.json          ← manifeste (pointe vers PROFILES/logo/CONTRACTS/)
    ├── CONTRACTS/
    │   ├── production_pack_schema_logo.json   ← schéma canonique logo (genre/n_angles/clip_source_ref/on_screen_text)
    │   ├── clipping_rules_logo.md             ← règles spécifiques logo (squelette)
    │   ├── casino_rules.md                    ← règles marques casino (squelette)
    │   ├── copywriting_doctrine_logo.md       ← doctrine copywriter logo (squelette)
    │   └── copywriter_systemprompt_logo.md    ← system prompt F04 logo (squelette)
    ├── F00_CAPTEURS_IN/
    │   └── clipping_sites_to_scrap_logo.example.json  ← sites de deals casino + trackers CPM
    └── ARCHIVUM/docs/                              ← knowledge spécifique logo (à remplir)
```

## Réalisation technique

`SHARED/profile_loader.py` expose :
- `load_profile(mode=None)` → lit `liber.mode` si mode None, retourne un `Profile`
- `Profile.resolve(key)` → chemin absolu (`pack_schema`, `copywriting_doctrine`, `copywriter_systemprompt`, `capteurs_sites_example`, `contracts_dir`)
- `Profile.rules_paths()` → liste des fichiers de règles
- `Profile.pack_shape` / `pack_nature` — métadonnées du pack

Les frégates différenciées (F00_CAPTEURS, F05 schema_validator, F02 critères, F04 doctrine/prompt) importent `load_profile` pour résoudre leurs fichiers.

## Statut

- ✅ Ossature (manifests, profile_loader, IW_CUSTOS init-siege, liber.mode) livrée
- ✅ Schéma canonique logo (production_pack_schema_logo.json) — `clip_source_ref` + `angles[genre/titre/body/on_screen_text/seo_tags/reframe_type]`
- ⏳ `PROFILES/logo/CONTRACTS/*` sont des **squelettes** à remplir par le Warsmith (researches casino/bannissement TT-YT-IG/FTC gambling/CPM Shortimiz/exemples captions reframes)
- ✅ Profil whop = heritage CONTRACTS/ (rien de cassé)
