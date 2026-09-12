{
  "sous_fregate_id": "F00B_VOX",
  "version": "1.0.0",
  "created_at": "2026-09-05",
  "parent": "F00_CAPTEURS",
  "statut": "actif",
  "description": "VOX = sous-frégate de F00_CAPTEURS. Assimilation des VODs Twitch (téléchargement partiel par segments HLS via yt-dlp) + extraction des moments candidats + scoring viral multicritère + Gate Warsmith + trail. F00 reste F00A (scan viral YouTube/RSS/Trends). VOX est déclenchée en amont du workflow PUR, AVANT F03_SOURCE_HUNTER.",

  "position_workflow": {
    "declenchement": "Après réception d'une ou plusieurs URLs VOD Twitch du Warsmith, avant F01_SCOUT en mode PUR",
    "ordre_pur": ["F00B_VOX", "F01_SCOUT", "F02_TYRANT_CAMP", "F03_SOURCE_HUNTER", "F04_COPYWRITER", "F05_PACKAGER", "F06_DIRECTOR"],
    "regle_position": "La position d'une frégate dépend de SA PLACE dans le workflow, pas d'un numéro figé",
    "peut_recevoir": ["URLs VOD Twitch", "Clips de référence", "Directives campagne (whop_directive.md)"],
    "peut_fournir": ["vox_manifest.json", "candidats.json", "scoring.json", "gate_verdict.json", "trail.json"]
  },

  "twitch_ingest": {
    "principe": "Jamais de téléchargement de VOD complète. Les VODs Twitch sont servies en segments HLS de ~10s ; on ne récupère que les segments entre les balises temporelles, en stream copy, sans recompression.",
    "outil": "yt-dlp + ffmpeg",
    "commande_modele": "yt-dlp --download-sections \"*HH:MM:SS-HH:MM:SS\" --force-keyframes-at-cuts -f \"bv*[height<=1080]+ba/b\" --concurrent-fragments 5 -o \"vox_ingest/{segment_id}.%(ext)s\" \"URL_VOD\"",
    "notes_cles": [
      "--download-sections : ne télécharge QUE les segments HLS entre start et end",
      "--force-keyframes-at-cuts : coupe propre sur keyframes (frame exacte garantie)",
      "-f bv*[height<=1080]+ba/b : qualité native 1080p max, pas de recompression",
      "Stream copy = résolution, FPS et bitrate identiques au stream original",
      "Budget par VOD : 10-20 minutes de matière max, jamais 8 heures"
    ],
    "fichiers": {
      "vox_ingest/": "Fichiers média bruts extraits (un fichier par segment demandé)"
    }
  },

  "candidats": {
    "definition": "Une CANDIDATE est une fenêtre brute de 20-40s (max 60s) repérée dans la matière téléchargée.",
    "detection": {
      "signaux": [
        "Rires du chat (timestamps Twitch Highlighter / réactions chat exportées)",
        "Changements brusques de volume/énergie vocale",
        "Rires, exclamations, silences courts = rythme de dialogue",
        "Mots déclencheurs (aussi, whammy, j'ai/have to, actually, listen)",
        "Fins de punchline suivies de réaction"
      ],
      "parametres": {
        "duree_cible": "20-40s",
        "duree_max": "60s",
        "pre_roll": "0-2s avant le signal",
        "post_roll": "1-3s après le signal",
        "overlap": "Les candidats peuvent se chevaucher, le dédoublonnage se fait au scoring"
      }
    }
  },

  "scoring_viral": {
    "formule": "score = w_h * hook_force + w_e * emotion + w_c * clarity + w_q * quotability + w_t * timing + w_f * format_fit",
    "poids_par_defaut": {"w_h": 0.30, "w_e": 0.25, "w_c": 0.15, "w_q": 0.15, "w_t": 0.10, "w_f": 0.05},
    "criteres": {
      "hook_force": "0-10. La première phrase arrête-t-elle le scroll ? Phrase choc, question, chiffre, conflit, intrique",
      "emotion": "0-10. Intensité émotionnelle : rire, indignation, surprise, tension, suspense",
      "clarity": "0-10. Compréhensible sans contexte ? Marche sans le son ?",
      "quotability": "0-10. Une phrase mémorable, citable, reprise en commentaire ?",
      "timing": "0-10. Rythme interne : peu de temps mort, un changement toutes les 2-4s",
      "format_fit": "0-10. Convient au format vertical 9:16 ? Visage/centré ? Recadrage 9:16 possible sans perdre l'action ?"
    },
    "bonus_maluses": [
      "+2 si le moment est confirmé par le clip de référence (même type d'humour/émotion)",
      "+1.5 si moment unique (pas déjà couvert par un autre candidat à ±15s)",
      "+1 si potentiel de série (le moment annonce une suite / boucle)",
      "-3 si durée > 60s",
      "-2 si besoin de contexte externe pour comprendre",
      "-2 si contenu à risque TOS (désint, contenu sensible hors directive)",
      "-1 si mouvement caméra brusque (recadrage 9:16 difficile)"
    ],
    "regles": [
      "Un candidat est noté sur chaque critère puis la formule pondérée est appliquée",
      "Le poids peut être ajusté par directive campagne (ex: pondérer emotion plus fort si la campagne demande du drame)",
      "Les candidats qui se chevauchent à plus de 50% sont fusionnés avant notation"
    ]
  },

  "gate_vox": {
    "type": "SOUS-FREGATE_GATE",
    "validateur": "Warsmith",
    "entree": "scoring.json classé",
    "sortie": "gate_verdict.json",
    "protocole": [
      "1. VOX propose N candidats (N = nb demandé par l'opérateur × 2 minimum, pour marge de sélection)",
      "2. Chaque candidat a son score + son top 2 hooks possibles + durée proposée",
      "3. Le Warsmith VALIDE, MODIFIE ou REJETTE chaque candidat",
      "4. gate_verdict.json enregistre : candidats validés (statut=trail_ready), modifiés (statut=trail_ready, ajustements), rejetés (statut=rejected, motif)",
      "5. Seuls les candidats trail_ready partent au trail",
      "6. Le trail part SEULEMENT après validation du gate — jamais avant"
    ],
    "regle_d_or": "Le Warsmith décide du NOMBRE de clips. VOX ne produit jamais plus que demandé + marge. Pas de clip sans verdict.",
    "rejet_automatique": [
      "score < 6.0 sauf si le Warsmith override",
      "chevauchement > 50% avec un candidat mieux noté",
      "durée hors [15s, 60s]",
      "contenu interdit par la directive campagne (voir ARCHIVUM/campaign/whop_directive.md)"
    ]
  },

  "trail": {
    "role": "Séquence de préparation des clips validés : chaque candidat trail_ready devient un trail_spec prêt pour F03/F06.",
    "etapes": [
      "Extraction précise du start/end définitifs (à ±0.5s) après validation",
      "Nettoyage : repérage des temps morts internes (>1.5s de silence sans visuel), points de coupure",
      "Détection des points de coupure : pauses, respirations, changements de plan, fins de phrase",
      "Choix du start : le trail commence sur le déclencheur (pas de préambule)",
      "Choix du end : sur une fin de punchline ou un rebond, jamais au milieu d'une phrase",
      "Génération du trail_spec.json par candidat : timestamps précis, cuts internes suggérés, hook potentiel, durée finale"
    ],
    "sortie": "trail.json",
    "remise": "F03_SOURCE_HUNTER reçoit trail.json (segments validés et pré-équipés)"
  },

  "fichiers": {
    "README_F00B_VOX.md": "Ce document",
    "CODEBASE/f00b_vox.py": "Script : ingest VOD partielle + détection candidats + scoring + gate + trail",
    "CODEBASE/requirements_f00b.txt": "Dépendances",
    "IN/": "Inputs (URLs VOD, directives, clips ref)",
    "OUT/": "Outputs (vox_manifest, candidats, scoring, gate_verdict, trail)",
    "TRACKING/F00B_LOG.md": "Journal"
  },

  "heresies_interdites": [
    "❌ Télécharger une VOD complète",
    "❌ Recompresser/rendre la vidéo (stream copy uniquement à ce stade)",
    "❌ Proposer plus de clips que demandé + marge de sélection",
    "❌ Envoyer au trail sans verdict de gate",
    "❌ Décider du style visuel final (rôle F06 + OMNIS_WATCH)",
    "❌ Écraser un verdict du Warsmith"
  ]
}
