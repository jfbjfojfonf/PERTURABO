#!/usr/bin/env python3
"""
campaign_directive_parser.py — Parse les directives campagne Clipify/Whop.

Lit un fichier directive markdown (format whop_directive_template.md)
et produit un campaign_directive.json structuré que les frégates consomment.

Usage :
    python campaign_directive_parser.py IN/directive.md
    python campaign_directive_parser.py IN/directive.md -o OUT/campaign_directive.json
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path


def parse_payout_block(text):
    """Extrait les règles de payout depuis le bloc Payment Details."""
    payouts = {}
    platform_names = {
        "tiktok": ["tiktok"],
        "twitter_x": ["x (twitter)", "twitter", "x"],
        "instagram_reels": ["ig reels", "instagram reels", "instagram"],
        "youtube_shorts": ["youtube shorts", "yt shorts"],
    }
    
    # Pattern: $15 per 50,000 views ou $15 per 50K views
    payout_pattern = r"\$(\d+)\s+per\s+([\d,]+)K?\s*views"
    
    for match in re.finditer(payout_pattern, text, re.IGNORECASE):
        amount = int(match.group(1))
        views_str = match.group(2).replace(",", "")
        views = int(views_str)
        # Si pas de K suffix et nombre < 1000, multiplier par 1000
        if not match.group(0).endswith("K views") and views < 1000:
            views *= 1000
        
        # Identifier la plateforme
        line_start = text.rfind("\n", 0, match.start()) + 1
        line = text[line_start:match.end()].lower()
        
        matched_platform = "default"
        for plat_key, aliases in platform_names.items():
            for alias in aliases:
                if alias in line:
                    matched_platform = plat_key
                    break
            if matched_platform != "default":
                break
        
        payouts[matched_platform] = {
            "payout_usd": amount,
            "views_per_unit": views,
        }
    
    return payouts


def parse_caption_rules(text):
    """Extrait les règles de caption/tagging par plateforme."""
    rules = {}
    platforms = {
        "tiktok": "TikTok",
        "twitter_x": "X \\(Twitter\\)|Twitter|X",
        "instagram_reels": "IG Reels|Instagram",
        "youtube_shorts": "YouTube Shorts|YT Shorts",
    }
    
    for key, pattern in platforms.items():
        # Chercher le bloc de la plateforme
        section_match = re.search(
            rf"###\s*({pattern})\s*\n(.*?)(?=###|\n##|\Z)",
            text, re.IGNORECASE | re.DOTALL
        )
        if section_match:
            block = section_match.group(2)
            rule = {"platform": key}
            
            # Handle tag
            handle_match = re.search(r"\*\*Handle tag:\*\*\s*@([\w.]+)", block)
            if handle_match:
                rule["handle"] = "@" + handle_match.group(1).strip()
            
            # Hashtags
            hash_match = re.search(r"\*\*Hashtags:\*\*\s*#\[?([^\]\n]+)\]?", block)
            if hash_match:
                rule["hashtags"] = ["#" + h.strip() for h in hash_match.group(1).split(",")]
            
            # Caption format
            cap_match = re.search(r"\*\*Caption format:\*\*\s*(.+)", block)
            if cap_match:
                rule["caption_format"] = cap_match.group(1).strip()
            
            # Caption keyword
            kw_match = re.search(r"\*\*Caption keyword:\*\*\s*\"(.+?)\"", block)
            if kw_match:
                rule["caption_keyword"] = kw_match.group(1)
            
            rules[key] = rule
    
    return rules


def parse_watermark_rules(text):
    """Extrait les règles watermark."""
    rules = {}
    
    opacity_match = re.search(r"[Oo]pacity.*?≥?\s*(\d+)%", text)
    if opacity_match:
        rules["opacity_min"] = int(opacity_match.group(1)) / 100
    
    pos_match = re.search(r"\*\*Position:\*\*\s*(\w+)", text)
    if pos_match:
        rules["position"] = pos_match.group(1).lower()
    
    # Exception platforms
    exception_match = re.search(r"[Ee]xception.*?optional for\s*\[?([^\]\n]+)\]?", text)
    if exception_match:
        rules["optional_for"] = [
            p.strip().lower().replace(" ", "_").replace("(", "").replace(")", "")
            for p in exception_match.group(1).split(",")
        ]
    
    return rules


def parse_anti_spam(text):
    """Extrait les règles anti-spam."""
    rules = []
    in_section = False
    
    for line in text.split("\n"):
        lower = line.lower()
        if "anti-spam" in lower or "anti spam" in lower or "posting rule" in lower:
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            stripped = line.strip()
            # Match ❌ ou - ❌ ou * ❌ ou simplement - (dash)
            if "❌" in stripped or stripped.startswith("- ") or stripped.startswith("* "):
                rule = stripped.replace("❌", "").replace("- ", "").replace("* ", "").strip()
                if rule and len(rule) > 5:
                    rules.append(rule)
    
    return rules


def parse_content_source(text):
    """Extrait les règles de source de contenu."""
    rules = {}
    
    # Approved period
    period_match = re.search(r"\*\*Approved content:\*\*\s*(.+)", text)
    if period_match:
        rules["approved_period"] = period_match.group(1).strip()
    
    # Restrictions
    restriction_matches = re.findall(r"- (.+restriction.+|.+No .+|.+not.+)", text, re.IGNORECASE)
    if restriction_matches:
        rules["restrictions"] = [r.strip() for r in restriction_matches[:5]]
    
    return rules


def parse_cycle(text):
    """Extrait les dates de cycle."""
    cycle = {}
    
    start_match = re.search(r"\*\*Start:\*\*\s*(\[?[\d\-/]+\]?)", text)
    if start_match:
        cycle["start"] = start_match.group(1).strip("[]")
    
    end_match = re.search(r"\*\*End:\*\*\s*(\[?[\d\-/]+\]?)", text)
    if end_match:
        cycle["end"] = end_match.group(1).strip("[]")
    
    return cycle


def parse_directive(filepath):
    """Parse complet d'un fichier directive markdown."""
    path = Path(filepath)
    if not path.exists():
        print(f"❌ Fichier introuvable : {filepath}")
        sys.exit(1)
    
    text = path.read_text(encoding="utf-8")
    
    # Campaign ID
    cid_match = re.search(r"Campaign ID:\s*(.+)", text)
    campaign_id = cid_match.group(1).strip().strip("*") if cid_match else path.stem
    
    # Creator name (première ligne)
    creator_match = re.search(r"^#\s+(.+?)(?:\s+x\s+Clipify|\s*$)", text, re.MULTILINE)
    creator_name = creator_match.group(1).strip() if creator_match else "unknown"
    
    # Platforms
    plat_match = re.search(r"\*\*Platforms:\*\*\s*(.+)", text)
    platforms = []
    if plat_match:
        platforms = [p.strip().strip("[]") for p in plat_match.group(1).split(",")]
    
    # Language
    lang_match = re.search(r"\*\*Language:\*\*\s*(.+)", text)
    language = lang_match.group(1).strip() if lang_match else "English"
    
    # Audience
    audience_match = re.search(r"\*\*Audience Tier:\*\*\s*(.+)", text)
    audience_tier = audience_match.group(1).strip() if audience_match else "Tier 1"
    
    # Payout
    payouts = parse_payout_block(text)
    
    # Min/Max payout
    min_match = re.search(r"\*\*Minimum Payout:\*\*\s*(.+)", text)
    min_payout = min_match.group(1).strip() if min_match else "50K views"
    
    max_match = re.search(r"\*\*Maximum Payout:\*\*\s*(.+)", text)
    max_payout = max_match.group(1).strip() if max_match else "$900"
    
    budget_match = re.search(r"\*\*Total Campaign Budget:\*\*\s*(.+)", text)
    budget = budget_match.group(1).strip() if budget_match else "$5000"
    
    # Build output
    directive = {
        "campaign_id": campaign_id,
        "creator_name": creator_name,
        "parsed_at": datetime.now().isoformat(),
        "source_file": str(path),
        
        "platforms": platforms,
        "language": language,
        "audience_tier": audience_tier,
        
        "payout": {
            "per_platform": payouts,
            "minimum": min_payout,
            "maximum": max_payout,
            "budget": budget,
            "methods": re.search(r"\*\*Payment Methods:\*\*\s*(.+)", text)
                       and re.search(r"\*\*Payment Methods:\*\*\s*(.+)", text).group(1).strip()
                       or "USDC, PayPal",
        },
        
        "caption_rules": parse_caption_rules(text),
        "watermark": parse_watermark_rules(text),
        "anti_spam": parse_anti_spam(text),
        "content_source": parse_content_source(text),
        "cycle": parse_cycle(text),
    }
    
    return directive


def main():
    if len(sys.argv) < 2:
        print("Usage: python campaign_directive_parser.py <directive.md> [-o output.json]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = None
    
    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            output_file = sys.argv[idx + 1]
    
    directive = parse_directive(input_file)
    
    if not output_file:
        output_file = str(Path(input_file).parent / "campaign_directive.json")
    
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(directive, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Directive parsée → {output_file}")
    print(f"   Creator: {directive['creator_name']}")
    print(f"   Platforms: {', '.join(directive['platforms'])}")
    print(f"   Payout: {len(directive['payout']['per_platform'])} plateformes configurées")


if __name__ == "__main__":
    main()
