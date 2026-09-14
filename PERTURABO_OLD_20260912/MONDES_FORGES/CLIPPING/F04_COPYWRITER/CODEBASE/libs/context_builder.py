"""
libs/context_builder.py — Phase A de F04_COPYWRITER
===================================================

Rassemble TOUT l'ARCHIVUM pertinent pour le copywriting clipping dans un
contexte structuré consommé par le modèle premium (Phase B) :

  - ARCHIVUM/copywriting/ (les 8 sous-dossiers + reference_clips_titles)
  - ARCHIVUM/rules/ (clipping_rules, whop_rules, platform_*)
  - ARCHIVUM/platform_generator/{p}_profile.md
  - ARCHIVUM/market_generator/{m}.md
  - ARCHIVUM/angles/ (angle_patterns.json, angle_performance.json)
  - ARCHIVUM/demons/ (exemples de titres gagnants)
  - ARCHIVUM/knowledge_base/ (sites, docs, transcripts)
  - ARCHIVUM/learnings/learnings.json
  - CONTRACTS/copywriting_doctrine.md, copywriter_systemprompt.md,
    anti_bullshit.md (si présent)
  - L'angle actif + le specimen source + le verdict campagne

Chaque fichier est tronqué à MAX_FILE_CHARS pour rester dans le contexte
du modèle premium sans diluer. Les fichiers manquants sont tracés
("introuvable") — la frégate n'invente jamais une source absente.
"""

import json
import os

MAX_FILE_CHARS = 30000


class ContextBuilder:
    def __init__(self, forge_root: str):
        self._forge_root = forge_root
        self._archivum = os.path.join(forge_root, "ARCHIVUM")
        self._contracts = os.path.join(forge_root, "CONTRACTS")

    def _load_spin_humour(self) -> str | None:
        """Source de vérité du spin humour : liber_clipping.json (inputs_warsmith)."""
        liber_path = os.path.join(self._forge_root, "liber_clipping.json")
        if not os.path.exists(liber_path):
            return None
        try:
            with open(liber_path, "r", encoding="utf-8") as f:
                liber = json.load(f)
            return liber.get("inputs_warsmith", {}).get("spin_humour") or None
        except (OSError, json.JSONDecodeError):
            return None

    # ------------------------------------------------------------------
    def _read(self, path: str, label: str) -> str:
        if not os.path.exists(path):
            return f"[introuvable: {label}]"
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError) as e:
            return f"[erreur lecture {label}: {e}]"
        if len(content) > MAX_FILE_CHARS:
            return content[:MAX_FILE_CHARS] + "\n[... TRONQUÉ — source > 30k chars]"
        return content

    def _walk(self, root: str, label: str, extensions: tuple = (".md", ".json", ".txt")) -> dict:
        result = {}
        if not os.path.isdir(root):
            return result
        for dirpath, _dirs, files in sorted(os.walk(root)):
            for name in sorted(files):
                if name.startswith(".") or not name.endswith(extensions):
                    continue
                full = os.path.join(dirpath, name)
                rel = os.path.relpath(full, root).replace("\\", "/")
                result[rel] = self._read(full, f"{label}/{rel}")
        return result

    # ------------------------------------------------------------------
    def collect_archivum(self, platform: str, market: str,
                         skip_transcripts: bool = False) -> dict:
        copywriting_root = os.path.join(self._archivum, "copywriting")
        rules_root = os.path.join(self._archivum, "rules")
        platform_profile = os.path.join(
            self._archivum, "platform_generator", f"{platform}_profile.md")
        market_profile = os.path.join(
            self._archivum, "market_generator", f"{market}.md")
        angles_dir = os.path.join(self._archivum, "angles")
        demons_dir = os.path.join(self._archivum, "demons")
        knowledge_root = os.path.join(self._archivum, "knowledge_base")
        learnings_path = os.path.join(self._archivum, "learnings", "learnings.json")

        knowledge_base = self._walk(knowledge_root, "knowledge_base")
        if skip_transcripts:
            knowledge_base = {
                k: v for k, v in knowledge_base.items()
                if not k.split("/", 1)[0] == "transcripts"
            }

        return {
            "copywriting_8_sous_dossiers": self._walk(copywriting_root, "copywriting"),
            "rules": self._walk(rules_root, "rules"),
            "platform_profile": self._read(platform_profile, f"{platform}_profile.md"),
            "market_profile": self._read(market_profile, f"{market}.md"),
            "angles": {
                "angle_patterns.json": self._read(
                    os.path.join(angles_dir, "angle_patterns.json"), "angle_patterns"),
                "angle_performance.json": self._read(
                    os.path.join(angles_dir, "angle_performance.json"), "angle_performance"),
            },
            "demons": self._walk(demons_dir, "demons"),
            "knowledge_base": knowledge_base,
            "learnings": self._read(learnings_path, "learnings.json"),
        }

    def collect_contracts(self) -> dict:
        doctrine = self._read(
            os.path.join(self._contracts, "copywriting_doctrine.md"), "doctrine")
        systemprompt = self._read(
            os.path.join(self._contracts, "copywriter_systemprompt.md"), "systemprompt")
        anti_bullshit = self._read(
            os.path.join(self._contracts, "anti_bullshit.md"), "anti_bullshit")
        return {
            "doctrine": doctrine,
            "systemprompt": systemprompt,
            "anti_bullshit": anti_bullshit,
        }

    # ------------------------------------------------------------------
    def _load_meme_v2_source(self) -> dict:
        path = os.path.join(self._forge_root, "F01_SCOUT", "OUT", "source_specimen.json")
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            return data.get("source_post") or {}
        except (OSError, json.JSONDecodeError):
            return {}

    # ------------------------------------------------------------------
    def build_logo(self, angle: dict, sub_mode: str, campaign: dict,
                   verdict: dict, platform: str, market: str) -> dict:
        """Contexte LOGO v2 : PAS de specimen F03 (le clip vient du Warsmith).

        Rassemble le clip source + l'article (informatif) OU la blague (humour)
        + le style du clip viral de référence + l'ARCHIVUM copywriting.

        En mode humour OU meme, injecte le spin humour du Warsmith (source de
        vérité : liber_clipping.json -> inputs_warsmith.spin_humour) pour
        orienter la forge.
        """
        spin_humour = self._load_spin_humour()
        meme_v2_source = self._load_meme_v2_source() if sub_mode == "meme_v2" else None
        return {
            "campaign_id": verdict.get("campaign_id"),
            "angle_id": angle.get("angle_id"),
            "sub_mode": sub_mode,
            "humour_spin": spin_humour if sub_mode in ("humour", "meme") else None,
            "meme_v2_source": meme_v2_source,
            "angle": {
                "angle_id": angle.get("angle_id"),
                "genre": angle.get("genre"),
                "title": angle.get("title"),
                "body": angle.get("body"),
                "on_screen_text": angle.get("on_screen_text"),
                "seo_tags": angle.get("seo_tags"),
                "angle_family": angle.get("angle_family"),
                "emotion_mode": angle.get("emotion_mode"),
                "engagement_type": angle.get("engagement_type"),
                "reframe_dim": angle.get("reframe_dim"),
                "zone": angle.get("zone"),
                "angle_brief": angle.get("angle_brief"),
                "source_post_id": angle.get("source_post_id"),
            },
            "clip_source_ref": campaign.get("reference_clip"),
            "article_source": campaign.get("article_source"),
            "joke_source": campaign.get("joke_source"),
            "keyword": campaign.get("keyword"),
            "meme_source": campaign.get("meme_source"),
            "reference_clip_style": campaign.get("reference_clip_style"),
            "verdict": verdict,
            "platform_target": platform,
            "market_target": market,
            "archivum": self.collect_archivum(platform, market, skip_transcripts=True),
            "contracts": self.collect_contracts(),
        }

    # ------------------------------------------------------------------
    def build(self, angle: dict, specimen: dict, verdict: dict,
              platform: str, market: str) -> dict:
        return {
            "campaign_id": verdict.get("campaign_id") or specimen.get("campaign_id"),
            "angle_id": angle.get("angle_id"),
            "angle": {
                "angle_family": angle.get("angle_family"),
                "emotion_mode": angle.get("emotion_mode"),
                "engagement_type": angle.get("engagement_type"),
                "reframe_dim": angle.get("reframe_dim"),
                "zone": angle.get("zone"),
                "blue_ocean_reframe_applied": angle.get("blue_ocean_reframe_applied"),
                "territory": angle.get("territory"),
                "weight": angle.get("weight"),
            },
            "specimen": specimen,
            "verdict": verdict,
            "platform_target": platform,
            "market_target": market,
            "archivum": self.collect_archivum(platform, market),
            "contracts": self.collect_contracts(),
        }
