"""
libs/skeleton_extractor.py — Extraction du squelette viral du clip de référence
================================================================================

En mode IRON (prepare), le squelette est extrait par l'IRON sandbox.
En mode auto, ce module fournit un cadre de pré-squelette déterministe
(hook_type, emotion_dominante, structure_narrative, loop_technique,
engagement_type) à partir des métadonnées disponibles du specimen.

Usage:
  from skeleton_extractor import SkeletonExtractor
  skel = SkeletonExtractor().preskeleton(reference_clip)
"""

import os


class SkeletonExtractor:
    def __init__(self, forge_root: str):
        self.forge_root = forge_root

    def preskeleton(self, reference_clip: dict) -> dict:
        """
        Pré-squelette déterministe à partir du clip de référence.
        Ne prétend pas remplacer l'IRON — il pré-remplit des champs vides
        pour que l'IRON n'ait qu'à confirmer/enrichir.
        """
        if not reference_clip:
            return {
                "hook_type": None,
                "emotion_dominante": None,
                "structure_narrative": None,
                "loop_technique": None,
                "engagement_type": None,
                "endroits_preuve": [],
                "iron_status": "pending",
            }

        skeleton = {
            "hook_type": None,
            "emotion_dominante": None,
            "structure_narrative": None,
            "loop_technique": None,
            "engagement_type": None,
            "endroits_preuve": [],
            "iron_status": "pending",
            "source_meta": {
                "url": reference_clip.get("url"),
                "title": reference_clip.get("title"),
                "view_count": reference_clip.get("view_count"),
                "duration_sec": reference_clip.get("duration_sec"),
                "platform": reference_clip.get("platform", "youtube"),
            },
        }

        # Heuristiques légères sur le titre (l'IRON confirmera)
        title = (reference_clip.get("title") or "").lower()
        if any(w in title for w in ["sad", "drame", "tragique", "perdu", "mort"]):
            skeleton["emotion_dominante"] = "drame"
        elif any(w in title for w in ["crazy", "insane", "outrage", "shocking"]):
            skeleton["emotion_dominante"] = "outrage"
        elif any(w in title for w in ["happy", "joie", "fun", "hilarious"]):
            skeleton["emotion_dominante"] = "joie"
        elif any(w in title for w in ["inspiring", "inspiration", "motivation"]):
            skeleton["emotion_dominante"] = "inspiration"

        if any(ch in title for ch in ["?", "how ", "why "]):
            skeleton["hook_type"] = "question"
        elif any(w in title for w in ["never", "always", "the truth", "dont"]):
            skeleton["hook_type"] = "declaration"

        return skeleton
