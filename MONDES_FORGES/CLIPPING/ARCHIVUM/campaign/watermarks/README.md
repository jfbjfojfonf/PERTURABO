# Watermarks — Règles de Gestion

## Stockage
Les fichiers watermark PNG sont stockés dans :
```
ARCHIVUM/campaign/watermarks/
├── [creator_name]_watermark.png
├── [creator_name]_watermark_preview.png
└── README.md
```

## Règles techniques

| Paramètre | Valeur | Notes |
|-----------|--------|-------|
| Format | PNG (transparency) | Toujours avec canal alpha |
| Opacité | ≥ 75% | Jamais en dessous |
| Position | Centré | Horizontalement + verticalement |
| Taille | Lisible sur mobile | Minimum 15% de la largeur vidéo |
| Fond | Transparent | Pas de fond blanc/colore |
| Résolution | ≥ 300px de large | Pour qualité 1080p |

## Usage par plateforme

| Plateforme | Watermark obligatoire ? | Notes |
|------------|------------------------|-------|
| TikTok | ✅ OUI | Centré, opacity ≥75% |
| IG Reels | ✅ OUI | Centré, opacity ≥75% |
| YouTube Shorts | ✅ OUI | Centré, opacity ≥75% |
| X (Twitter) | ⚠️ Optionnel | Si fourni, même specs |

## Intégration dans le pack

Le watermark est inclus dans le `production_pack.json` par F05_PACKAGER :

```json
{
  "watermark": {
    "file": "watermark.png",
    "opacity": 0.80,
    "position": "center",
    "size_pct": 15,
    "platforms_obliged": ["tiktok", "instagram_reels", "youtube_shorts"],
    "platforms_optional": ["twitter_x"]
  }
}
```

## Checklist avant soumission
- [ ] Watermark visible sur toute la durée du clip
- [ ] Opacité ≥ 75% (vérifier sur fond sombre ET clair)
- [ ] Lisible sur écran mobile (test 360p)
- [ ] Aucun autre logo/promotion visible
- [ ] Position centrée (pas décalé vers un coin)
