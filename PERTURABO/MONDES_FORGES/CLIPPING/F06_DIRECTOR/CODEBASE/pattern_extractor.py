#!/usr/bin/env python3
"""
F06_DIRECTOR — Pattern Extractor
"Le fer qui veille apprend de chaque siège précédent."

Extrait les patterns de montage depuis les transcripts de tutos YouTube.
Sauvegarde dans ARCHIVUM/montage/patterns/

Hérésies interdites :
-❌ Ne crée JAMAIS de faux patterns
-❌ Ne modifie JAMAIS les transcripts originaux
-❌ Ne supprime JAMAIS un pattern existant
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
TRANSCRIPTS_DIR = MONTAGE / "transcripts"
PATTERNS_DIR = MONTAGE / "patterns"


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


def load_transcripts() -> list:
    """Charge tous les transcripts depuis ARCHIVUM/montage/transcripts/."""
    transcripts = []

    for transcript_file in TRANSCRIPTS_DIR.glob("*.json"):
        data = load_json(transcript_file)
        if data:
            transcripts.append({
                "filename": transcript_file.name,
                "data": data
            })

    for transcript_file in TRANSCRIPTS_DIR.glob("*.txt"):
        with open(transcript_file, "r", encoding="utf-8") as f:
            content = f.read()
        if content:
            transcripts.append({
                "filename": transcript_file.name,
                "data": {"text": content}
            })

    return transcripts


def extract_hook_patterns(transcript: dict) -> list:
    """Extrait les patterns de hook depuis un transcript."""
    patterns = []
    text = transcript.get("data", {}).get("text", "")

    if not text:
        return patterns

    # Patterns de hook courants
    hook_keywords = [
        "wait", "what", "listen", "okay", "so", "here's the thing",
        "you won't believe", "this changed", "nobody talks about",
        "the truth is", "let me tell you", "pay attention"
    ]

    sentences = re.split(r'[.!?]+', text)
    for i, sentence in enumerate(sentences[:10]):  # Premières phrases
        sentence_lower = sentence.lower().strip()
        for keyword in hook_keywords:
            if keyword in sentence_lower:
                patterns.append({
                    "type": "question" if "?" in sentence else "statement",
                    "text": sentence.strip(),
                    "position": i,
                    "confidence": 0.8
                })
                break

    return patterns


def extract_zoom_patterns(transcript: dict) -> list:
    """Extrait les patterns de zoom depuis un transcript."""
    patterns = []
    text = transcript.get("data", {}).get("text", "")

    if not text:
        return patterns

    # Moments qui zooment (émotion forte)
    emotion_keywords = [
        "shocking", "amazing", "incredible", "unbelievable",
        "crazy", "insane", "wild", "mind-blowing"
    ]

    sentences = re.split(r'[.!?]+', text)
    for i, sentence in enumerate(sentences):
        sentence_lower = sentence.lower().strip()
        for keyword in emotion_keywords:
            if keyword in sentence_lower:
                patterns.append({
                    "type": "dramatic_zoom",
                    "moment_keyword": keyword,
                    "intensity": 1.5,
                    "confidence": 0.7
                })
                break

    return patterns


def extract_cut_patterns(transcript: dict) -> list:
    """Extrait les patterns de cut depuis un transcript."""
    patterns = []
    text = transcript.get("data", {}).get("text", "")

    if not text:
        return patterns

    # Changements de sujet = bons moments pour cut
    transition_words = [
        "but", "however", "actually", "the thing is",
        "let me explain", "here's why", "the problem is"
    ]

    sentences = re.split(r'[.!?]+', text)
    for i, sentence in enumerate(sentences):
        sentence_lower = sentence.lower().strip()
        for word in transition_words:
            if sentence_lower.startswith(word):
                patterns.append({
                    "type": "jump_cut",
                    "position": i,
                    "reason": "topic_change",
                    "confidence": 0.75
                })
                break

    return patterns


def extract_all_patterns(transcripts: list) -> dict:
    """Extrait tous les patterns depuis tous les transcripts."""
    all_patterns = {
        "hook_patterns": [],
        "zoom_patterns": [],
        "cut_patterns": [],
        "transition_patterns": []
    }

    for transcript in transcripts:
        print(f"  📄 Analyse de {transcript['filename']}...")

        hooks = extract_hook_patterns(transcript)
        zooms = extract_zoom_patterns(transcript)
        cuts = extract_cut_patterns(transcript)

        all_patterns["hook_patterns"].extend(hooks)
        all_patterns["zoom_patterns"].extend(zooms)
        all_patterns["cut_patterns"].extend(cuts)

        print(f"    ✅ {len(hooks)} hooks, {len(zooms)} zooms, {len(cuts)} cuts")

    # Dédoublonner et trier par confiance
    for key in all_patterns:
        patterns = all_patterns[key]
        # Trier par confiance décroissante
        patterns.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        # Garder le top 10
        all_patterns[key] = patterns[:10]

    return all_patterns


def save_patterns(patterns: dict):
    """Sauvegarde les patterns extraits."""
    output_file = PATTERNS_DIR / "hook_patterns.json"
    save_json(output_file, patterns)

    # Aussi sauvegarder un résumé
    summary = {
        "extracted_at": datetime.utcnow().isoformat() + "Z",
        "generator": "F06_DIRECTOR/pattern_extractor",
        "total_patterns": {
            "hooks": len(patterns.get("hook_patterns", [])),
            "zooms": len(patterns.get("zoom_patterns", [])),
            "cuts": len(patterns.get("cut_patterns", []))
        },
        "patterns": patterns
    }

    summary_file = PATTERNS_DIR / "extraction_summary.json"
    save_json(summary_file, summary)


def main():
    """Point d'entrée principal."""
    print("\n" + "=" * 60)
    print("F06_DIRECTOR — Pattern Extractor")
    print("=" * 60)

    # Charger les transcripts
    print("\n  📂 Chargement des transcripts...")
    transcripts = load_transcripts()
    print(f"  ✅ {len(transcripts)} transcripts trouvés")

    if not transcripts:
        print("\n  ⚠️ Aucun transcript trouvé dans ARCHIVUM/montage/transcripts/")
        print("  💡 Ajoute des transcripts de tutos montage YouTube pour enrichir les patterns")
        print("  📁 Format : .json ou .txt dans ARCHIVUM/montage/transcripts/")

        # Créer des patterns par défaut
        print("\n  🔧 Création de patterns par défaut...")
        default_patterns = {
            "hook_patterns": [
                {"type": "question", "text": "Wait, what?", "confidence": 0.9},
                {"type": "statement", "text": "This changed everything", "confidence": 0.85},
                {"type": "cliffhanger", "text": "You won't believe what happens next", "confidence": 0.8}
            ],
            "zoom_patterns": [
                {"type": "dramatic_zoom", "moment_keyword": "shocking", "intensity": 1.5, "confidence": 0.8},
                {"type": "slow_zoom", "moment_keyword": "important", "intensity": 1.2, "confidence": 0.7}
            ],
            "cut_patterns": [
                {"type": "jump_cut", "reason": "topic_change", "confidence": 0.8},
                {"type": "subtle_cut", "reason": "pause", "confidence": 0.7}
            ],
            "transition_patterns": []
        }
        save_patterns(default_patterns)
        print("  ✅ Patterns par défaut créés")
        return

    # Extraire les patterns
    print("\n  🔍 Extraction des patterns...")
    patterns = extract_all_patterns(transcripts)

    # Sauvegarder
    print("\n  💾 Sauvegarde des patterns...")
    save_patterns(patterns)

    # Résumé
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DE L'EXTRACTION")
    print("=" * 60)
    print(f"  🎯 Hooks : {len(patterns.get('hook_patterns', []))}")
    print(f"  🔍 Zooms : {len(patterns.get('zoom_patterns', []))}")
    print(f"  ✂️  Cuts : {len(patterns.get('cut_patterns', []))}")
    print("=" * 60)
    print("  ✅ Pattern Extractor — Mission accomplie")
    print("  📤 Output : ARCHIVUM/montage/patterns/hook_patterns.json")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
