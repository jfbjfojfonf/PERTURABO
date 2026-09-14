#!/usr/bin/env python3
"""
F06_DIRECTOR — Le Directeur de Montage
"Une campagne est une forteresse. Le montage est l'artillerie qui ouvre la brèche."

F06 reçoit le segment (F03), le text_payload (F04), et le contexte.
Il lit ARCHIVUM/montage/ (patterns + rules + learnings).
Il produit montage_instructions.json — le guide ultime pour OMNIS_WATCH.

Hérésies interdites :
-❌ Ne touche JAMAIS à la vidéo
-❌ Ne décide JAMAIS du contenu (c'est F02/F04)
-❌ Ne poste JAMAIS (c'est l'opérateur)
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# ─── Paths ───────────────────────────────────────────────────────────────────
BASE = Path(__file__).resolve().parent.parent.parent  # MONDES_FORGES/CLIPPING
ARCHIVUM = BASE / "ARCHIVUM"
MONTAGE = ARCHIVUM / "montage"
PATTERNS_DIR = MONTAGE / "patterns"
RULES_DIR = MONTAGE / "rules"
LEARNINGS_DIR = ARCHIVUM / "learnings"
F06_OUT = BASE / "F06_DIRECTOR" / "OUT"


def load_json(path: Path) -> dict:
    """Charge un fichier JSON. Retourne {} si absent."""
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    """Sauvegarde un fichier JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  ✅ Sauvegardé : {path}")


def load_platform_rules(platform: str) -> dict:
    """Charge les règles de montage pour une plateforme donnée."""
    rules_file = RULES_DIR / f"{platform}.md"
    if not rules_file.exists():
        print(f"  ⚠️ Pas de règles pour {platform}, utilisation des défauts")
        return get_default_rules()

    with open(rules_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse les règles depuis le markdown
    return parse_rules_md(content, platform)


def get_default_rules() -> dict:
    """Règles de montage par défaut."""
    return {
        "platform": "youtube_shorts",
        "max_duration_sec": 60,
        "hook_duration_sec": 3,
        "aspect_ratio": "9:16",
        "cut_density": "high",
        "zoom_enabled": True,
        "text_overlay_enabled": True,
        "pacing": "fast"
    }


def parse_rules_md(content: str, platform: str) -> dict:
    """Parse de façon tolérante les règles Markdown du profil plateforme."""
    rules = {
        "platform": platform,
        "max_duration_sec": 60,
        "hook_duration_sec": 3,
        "aspect_ratio": "9:16",
        "cut_density": "high",
        "zoom_enabled": True,
        "text_overlay_enabled": True,
        "pacing": "fast"
    }

    def first_number(value: str, default: int) -> int:
        match = re.search(r"\d+", value)
        return int(match.group()) if match else default

    for raw_line in content.splitlines():
        line = raw_line.strip()
        lower = line.lower()
        if line.startswith("- **Hook**"):
            rules["hook_duration_sec"] = first_number(line, rules["hook_duration_sec"])
        elif line.startswith("- **Durée max**"):
            rules["max_duration_sec"] = first_number(line, rules["max_duration_sec"])
        elif line.startswith("- **Format**"):
            rules["aspect_ratio"] = line.split(":", 1)[-1].strip()
        elif line.startswith("- **Rythme**"):
            rules["pacing"] = line.split(":", 1)[-1].strip()
        elif line.startswith("- **Zoom**"):
            rules["zoom_enabled"] = "oui" in lower or "yes" in lower or "✅" in line
        elif line.startswith("- **Texte à l'écran**"):
            rules["text_overlay_enabled"] = "oui" in lower or "yes" in lower or "✅" in line
        elif line.startswith("- **Densité des cuts**"):
            rules["cut_density"] = line.split(":", 1)[-1].strip().lower()

    return rules


def load_patterns() -> dict:
    """Charge les patterns de montage depuis ARCHIVUM/montage/patterns/."""
    patterns = {
        "hook_patterns": [],
        "zoom_patterns": [],
        "cut_patterns": [],
        "transition_patterns": []
    }

    for pattern_file in PATTERNS_DIR.glob("*.json"):
        data = load_json(pattern_file)
        for key in patterns:
            if key in data:
                patterns[key].extend(data[key])

    return patterns


def load_learnings() -> dict:
    """Charge les learnings des campagnes précédentes."""
    learnings_file = LEARNINGS_DIR / "learnings.json"
    return load_json(learnings_file)


def build_montage_context(segment: dict, text_payload: dict, context: dict) -> dict:
    """Construit le contexte pour la génération des instructions."""
    return {
        "segment": segment,
        "text_payload": text_payload,
        "campaign": context.get("campaign", {}),
        "platform": context.get("platform", "youtube_shorts"),
        "market": context.get("market", "us_young_english"),
        "mode": context.get("mode", "pur"),
        "emotion": context.get("emotion", "neutral"),
        "energy_level": context.get("energy_level", "high")
    }


def generate_hook_instructions(context: dict, patterns: dict, rules: dict) -> dict:
    """Génère les instructions pour le hook (3 premières secondes)."""
    hook_duration = rules.get("hook_duration_sec", 3)
    platform = rules.get("platform", "youtube_shorts")

    # Sélection du pattern de hook selon l'émotion
    emotion = context.get("emotion", "neutral")
    hook_patterns = patterns.get("hook_patterns", [])

    selected_pattern = None
    for pattern in hook_patterns:
        if pattern.get("emotion") == emotion or pattern.get("emotion") == "any":
            selected_pattern = pattern
            break

    if not selected_pattern and hook_patterns:
        selected_pattern = hook_patterns[0]

    hook = {
        "duration_sec": hook_duration,
        "type": selected_pattern.get("type", "statement") if selected_pattern else "statement",
        "template": selected_pattern.get("template", "This changed everything") if selected_pattern else "This changed everything",
        "text_overlay": {
            "enabled": True,
            "position": "center",
            "font_size": 72,
            "color": "#FFFFFF",
            "animation": "pop_in",
            "duration_sec": hook_duration
        },
        "zoom": {
            "enabled": rules.get("zoom_enabled", True),
            "type": "slow_zoom",
            "intensity": 1.3,
            "target": "face"
        },
        "sound_effect": {
            "type": "subtle_whoosh",
            "timing": "start"
        }
    }

    return hook


def generate_body_instructions(context: dict, segment: dict, patterns: dict, rules: dict) -> dict:
    """Génère les instructions pour le corps du clip."""
    total_duration = segment.get("duration_sec", 45)
    hook_duration = rules.get("hook_duration_sec", 3)
    body_duration = total_duration - hook_duration

    body = {
        "duration_sec": body_duration,
        "cuts": generate_cuts(body_duration, context, rules),
        "zooms": generate_zooms(body_duration, context, rules),
        "text_overlays": generate_text_overlays(context, rules),
        "transitions": generate_transitions(context, rules),
        "pacing": rules.get("pacing", "fast"),
        "energy_curve": generate_energy_curve(body_duration, context)
    }

    return body


def generate_cuts(duration: int, context: dict, rules: dict) -> list:
    """Génère les instructions de cut."""
    density = rules.get("cut_density", "high")

    # Calcul du nombre de cuts selon la densité
    if density == "high":
        cut_interval = 2
    elif density == "very_high":
        cut_interval = 1
    elif density == "medium":
        cut_interval = 4
    else:
        cut_interval = 6

    cuts = []
    current_time = 0

    while current_time < duration:
        cut_type = "jump_cut" if current_time % 4 == 0 else "subtle_cut"
        cuts.append({
            "type": cut_type,
            "moment": format_time(current_time),
            "duration_sec": cut_interval,
            "intensity": 0.8 if cut_type == "jump_cut" else 0.5
        })
        current_time += cut_interval

    return cuts


def generate_zooms(duration: int, context: dict, rules: dict) -> list:
    """Génère les instructions de zoom."""
    if not rules.get("zoom_enabled", True):
        return []

    zooms = []
    emotion = context.get("emotion", "neutral")

    # Zoom sur les moments clés
    key_moments = [0.3, 0.6, 0.9]  # 30%, 60%, 90% de la durée

    for ratio in key_moments:
        moment = int(duration * ratio)
        zoom_type = "dramatic_zoom" if emotion in ["shock", "outrage"] else "slow_zoom"
        zooms.append({
            "type": zoom_type,
            "moment": format_time(moment),
            "intensity": 1.5 if emotion in ["shock", "outrage"] else 1.2,
            "target": "face",
            "duration_sec": 2
        })

    return zooms


def generate_text_overlays(context: dict, rules: dict) -> list:
    """Génère les instructions de texte à l'écran."""
    if not rules.get("text_overlay_enabled", True):
        return []

    overlays = []
    text_payload = context.get("text_payload", {})

    # Titre principal
    title = text_payload.get("title", "WAIT FOR IT")
    overlays.append({
        "type": "title",
        "text": title,
        "position": "top_center",
        "font_size": 64,
        "color": "#FF0000",
        "font": "bold",
        "animation": "pop_in",
        "duration_sec": 3
    })

    # Sous-titres (word by word)
    caption = text_payload.get("caption", "")
    if caption:
        overlays.append({
            "type": "subtitle",
            "text": caption,
            "position": "bottom",
            "font_size": 36,
            "color": "#FFFFFF",
            "animation": "word_by_word",
            "word_by_word": True
        })

    # Hashtags
    hashtags = text_payload.get("hashtags", [])
    if hashtags:
        overlays.append({
            "type": "hashtags",
            "text": " ".join(hashtags[:5]),
            "position": "bottom_right",
            "font_size": 24,
            "color": "#AAAAAA",
            "animation": "fade_in",
            "duration_sec": 5
        })

    return overlays


def generate_transitions(context: dict, rules: dict) -> list:
    """Génère les instructions de transition."""
    transitions = []
    emotion = context.get("emotion", "neutral")

    # Transition d'ouverture
    transitions.append({
        "type": "hard_cut",
        "moment": "0:00",
        "from": "black",
        "to": "clip_start"
    })

    # Transitions internes (selon l'émotion)
    if emotion in ["shock", "outrage"]:
        transitions.append({
            "type": "flash",
            "moment": "hook_end",
            "duration_sec": 0.1
        })

    # Transition de fin
    transitions.append({
        "type": "fade_to_black",
        "moment": "clip_end",
        "duration_sec": 0.5
    })

    return transitions


def generate_energy_curve(duration: int, context: dict) -> list:
    """Génère la courbe d'énergie du clip."""
    emotion = context.get("emotion", "neutral")

    if emotion in ["shock", "outrage"]:
        return [
            {"moment": "0:00", "energy": 100},
            {"moment": format_time(int(duration * 0.2)), "energy": 70},
            {"moment": format_time(int(duration * 0.5)), "energy": 90},
            {"moment": format_time(int(duration * 0.8)), "energy": 100},
            {"moment": format_time(duration), "energy": 60}
        ]
    else:
        return [
            {"moment": "0:00", "energy": 100},
            {"moment": format_time(int(duration * 0.3)), "energy": 60},
            {"moment": format_time(int(duration * 0.6)), "energy": 80},
            {"moment": format_time(duration), "energy": 50}
        ]


def generate_outro_instructions(context: dict, rules: dict) -> dict:
    """Génère les instructions pour l'outro."""
    outro = {
        "duration_sec": 2,
        "type": "fade_to_black",
        "text_overlay": {
            "enabled": True,
            "text": "Follow for more",
            "position": "center",
            "font_size": 48,
            "color": "#FFFFFF",
            "animation": "fade_in"
        },
        "sound_effect": {
            "type": "subtle_swoosh",
            "timing": "end"
        }
    }

    return outro


def format_time(seconds: int) -> str:
    """Convertit des secondes en format MM:SS."""
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes}:{secs:02d}"


def generate_montage_instructions(segment: dict, text_payload: dict, context: dict) -> dict:
    """Fonction principale : génère les instructions de montage complètes."""
    print("\n🎬 F06_DIRECTOR — Génération des instructions de montage")
    print("=" * 60)

    # 1. Charger les règles de la plateforme
    platform = context.get("platform", "youtube_shorts")
    print(f"\n  📋 Plateforme : {platform}")
    rules = load_platform_rules(platform)
    print(f"  ✅ Règles chargées : {rules.get('max_duration_sec', 60)}s max, hook {rules.get('hook_duration_sec', 3)}s")

    # 2. Charger les patterns
    print("\n  🔍 Chargement des patterns...")
    patterns = load_patterns()
    print(f"  ✅ {len(patterns.get('hook_patterns', []))} hook patterns, {len(patterns.get('zoom_patterns', []))} zoom patterns")

    # 3. Charger les learnings
    print("\n  📚 Chargement des learnings...")
    learnings = load_learnings()
    print(f"  ✅ {learnings.get('total_packs', 0)} packs analysés")

    # 4. Construire le contexte
    print("\n  🔧 Construction du contexte...")
    montage_context = build_montage_context(segment, text_payload, context)

    # 5. Générer les instructions
    print("\n  🎨 Génération des instructions...")

    instructions = {
        "metadata": {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "generator": "F06_DIRECTOR",
            "version": "1.0.0",
            "campaign_id": context.get("campaign", {}).get("id", "unknown"),
            "angle_id": context.get("angle_id", "unknown"),
            "segment_id": segment.get("id", "unknown")
        },
        "segment": {
            "source_url": segment.get("source_url", ""),
            "start_sec": segment.get("start_sec", 0),
            "end_sec": segment.get("end_sec", 60),
            "duration_sec": segment.get("duration_sec", 60),
            "transcript_segment": segment.get("transcript_segment", "")
        },
        "hook": generate_hook_instructions(montage_context, patterns, rules),
        "body": generate_body_instructions(montage_context, segment, patterns, rules),
        "outro": generate_outro_instructions(montage_context, rules),
        "text_payload": {
            "titles": text_payload.get("titles", []),
            "caption": text_payload.get("caption", ""),
            "hashtags": text_payload.get("hashtags", []),
            "on_screen_text": text_payload.get("on_screen_text", ""),
            "cta": text_payload.get("cta", "")
        },
        "platform_rules": rules,
        "style": {
            "pacing": rules.get("pacing", "fast"),
            "energy_level": context.get("energy_level", "high"),
            "color_palette": context.get("color_palette", "vibrant"),
            "text_treatment": context.get("text_treatment", "bold")
        },
        "compliance": {
            "disclosure": "#ad",
            "submit_deadline_min": 60,
            "platform": platform
        }
    }

    print("  ✅ Instructions générées avec succès")

    return instructions


def main():
    """Point d'entrée principal."""
    print("\n" + "=" * 60)
    print("F06_DIRECTOR — Le Directeur de Montage")
    print("=" * 60)

    # Vérifier les arguments
    if len(sys.argv) < 4:
        print("\n  ❌ Usage : python director.py <segment.json> <text_payload.json> <context.json>")
        print("  ❌ Exemple : python director.py F03_OUT/segment.json F04_OUT/text_payload.json context.json")
        sys.exit(1)

    segment_path = Path(sys.argv[1])
    text_payload_path = Path(sys.argv[2])
    context_path = Path(sys.argv[3])

    # Charger les entrées
    print(f"\n  📂 Chargement des entrées...")
    segment = load_json(segment_path)
    text_payload = load_json(text_payload_path)
    context = load_json(context_path)

    if not segment:
        print("  ❌ Segment vide ou introuvable")
        sys.exit(1)

    if not text_payload:
        print("  ❌ Text payload vide ou introuvable")
        sys.exit(1)

    print(f"  ✅ Segment : {segment.get('id', 'unknown')} ({segment.get('duration_sec', '?')}s)")
    print(f"  ✅ Text payload : {len(text_payload.get('titles', []))} titres")
    print(f"  ✅ Contexte : {context.get('platform', '?')}/{context.get('market', '?')}")

    # Générer les instructions
    instructions = generate_montage_instructions(segment, text_payload, context)

    # Sauvegarder
    output_file = F06_OUT / "montage_instructions.json"
    save_json(output_file, instructions)

    # Résumé
    print("\n" + "=" * 60)
    print("📦 RÉSUMÉ DES INSTRUCTIONS DE MONTAGE")
    print("=" * 60)
    print(f"  🎬 Hook : {instructions['hook']['duration_sec']}s ({instructions['hook']['type']})")
    print(f"  📹 Corps : {instructions['body']['duration_sec']}s ({len(instructions['body']['cuts'])} cuts)")
    print(f"  🎯 Outro : {instructions['outro']['duration_sec']}s")
    print(f"  📝 Text overlays : {len(instructions['body']['text_overlays'])}")
    print(f"  🔍 Zooms : {len(instructions['body']['zooms'])}")
    print(f"  🔄 Transitions : {len(instructions['body']['transitions'])}")
    print(f"  ⏱️  Durée totale : {segment.get('duration_sec', '?')}s")
    print("=" * 60)
    print("  ✅ F06_DIRECTOR — Mission accomplie")
    print("  📤 Output : F06_DIRECTOR/OUT/montage_instructions.json")
    print("  ⏳ Prochaine étape : F05_PACKAGER embarque les instructions")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
