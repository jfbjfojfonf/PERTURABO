"""
export_siege.py — Export des artefacts de siège en dossier humainement lisible
==============================================================================

Après validation de la Porte 4, génère un dossier EXPORT_* contenant :
- Mode Chaîne : CHAÎNE/ (nom, desc, tags, visuels) + VIDÉO_001/ (script, metadata, thumbnail)
- Mode Vidéo : VIDÉO_NNN/ (script, metadata, thumbnail)

Convertit les JSON des frégates en MD/TXT lisible pour le Warsmith.

Usage:
  python export_siege.py --mode channel --channel-slug the_stormist
  python export_siege.py --mode video --channel-slug the_stormist --video-number 2
"""

import argparse
import json
import os
import shutil
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ORCH_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_ORCH_DIR)

_F01_OUT = os.path.join(_PROJECT_ROOT, "F01_SENTINEL", "OUT")
_F02_OUT = os.path.join(_PROJECT_ROOT, "F02_BREACHER", "OUT")
_F03_OUT = os.path.join(_PROJECT_ROOT, "F03_FORGEWARD", "OUT")
_F04_OUT = os.path.join(_PROJECT_ROOT, "F04_HERALD", "OUT")
_F05_OUT = os.path.join(_PROJECT_ROOT, "F05_GRAND_COMPASS", "OUT")
_F06_OUT = os.path.join(_PROJECT_ROOT, "F06_IDENTITY_FORGE", "OUT")
_CHANNELS_DIR = os.path.join(_PROJECT_ROOT, "ARCHIVUM", "channels")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_write(dir_path, filename, content):
    os.makedirs(dir_path, exist_ok=True)
    path = os.path.join(dir_path, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def safe_copy(src, dest_dir, dest_name=None):
    if not os.path.exists(src):
        return False
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, dest_name or os.path.basename(src))
    shutil.copy2(src, dest)
    return True


def export_channel_identity(identity, export_dir):
    """Exporte l'identité de chaîne en fichiers lisible."""
    chan_dir = os.path.join(export_dir, "CHAÎNE")
    os.makedirs(chan_dir, exist_ok=True)

    # Nom + handle
    chosen = identity.get("chosen_name", identity.get("channel_names", [{}])[0].get("name", "N/A"))
    handle = identity.get("chosen_handle", "@" + chosen.lower().replace(" ", ""))
    safe_write(chan_dir, "nom.txt", chosen)
    safe_write(chan_dir, "handle.txt", handle)

    # Description
    desc = identity.get("description", "N/A")
    safe_write(chan_dir, "description.md", desc)

    # Tags
    tags = identity.get("tags", [])
    safe_write(chan_dir, "tags.txt", ", ".join(tags))

    # Tone of voice
    tov = identity.get("tone_of_voice", {})
    tov_md = f"""# Tone of Voice — {chosen}

## Registre
{tov.get('register', 'N/A')}

## Rythme
{tov.get('rhythm', 'N/A')}

## Vocabulaire signature
{tov.get('signature_vocabulary', 'N/A')}

## Personnalité
{tov.get('personality', 'N/A')}

## Ce que la chaîne ne FAIT JAMAIS
"""
    for item in tov.get("never_does", []):
        tov_md += f"- {item}\n"
    safe_write(chan_dir, "tone_of_voice.md", tov_md)

    # Codes visuels
    vc = identity.get("visual_codes", {})
    vc_md = f"""# Codes Visuels — {chosen}

## Palette de couleurs
{vc.get('color_palette', 'N/A')}

## Style graphique
{vc.get('graphic_style', 'N/A')}

## Template miniature
{vc.get('thumbnail_template', 'N/A')}

## Typographie
{vc.get('typography', 'N/A')}
"""
    safe_write(chan_dir, "codes_visuels.md", vc_md)

    # Format standard
    fs = identity.get("format_standard", {})
    fs_md = f"""# Format Standard — {chosen}

## Durée cible
{fs.get('target_duration', 'N/A')}

## Types par vidéo
{fs.get('types_per_video', 'N/A')}

## Structure
{fs.get('structure', 'N/A')}

## Fréquence de publication
{fs.get('publish_frequency', 'N/A')}
"""
    safe_write(chan_dir, "format_standard.md", fs_md)

    # 10 noms classés
    names = identity.get("channel_names", [])
    if names:
        names_md = f"# 10 Noms de chaîne classés\n\n"
        for n in names:
            names_md += f"## #{n.get('rank', '?')} — {n.get('name', 'N/A')}\n"
            names_md += f"{n.get('rationale', '')}\n\n"
            names_md += f"- Mémorabilité: {n.get('memorability_score', '?')}/10\n"
            names_md += f"- SEO: {n.get('seo_score', '?')}/10\n"
            names_md += f"- Marque: {n.get('brand_score', '?')}/10\n\n---\n\n"
        safe_write(chan_dir, "10_noms_classés.md", names_md)

    # Visuels
    banner_src = os.path.join(_F06_OUT, "banner.png")
    logo_src = os.path.join(_F06_OUT, "logo.png")
    if not os.path.exists(banner_src):
        banner_src = os.path.join(_CHANNELS_DIR, identity.get("channel_slug", ""), "banner.png")
    if not os.path.exists(logo_src):
        logo_src = os.path.join(_CHANNELS_DIR, identity.get("channel_slug", ""), "logo.png")

    safe_copy(banner_src, chan_dir, "banner.png")
    safe_copy(logo_src, chan_dir, "logo.png")

    print(f"  ✅ CHAÎNE/ — nom, description, tags, tone, codes visuels, format, banner, logo")
    return chosen, handle


def export_video(video_num, export_dir, video_prefix="VIDÉO"):
    """Exporte une vidéo (script + metadata + thumbnail) en fichiers lisible."""
    video_dir_name = f"{video_prefix}_{video_num:03d}"
    video_dir = os.path.join(export_dir, video_dir_name)
    os.makedirs(video_dir, exist_ok=True)

    # Script JSON → MD lisible
    script_data = load_json(os.path.join(_F03_OUT, "script.json"))
    if script_data:
        # script.md — version lisible
        script_md = f"# {script_data.get('title', 'N/A')}\n\n"
        script_md += f"**Niche**: {script_data.get('niche', 'N/A')}\n"
        script_md += f"**Format**: {script_data.get('format', 'N/A')}\n"
        script_md += f"**Durée cible**: {script_data.get('duree_cible', 'N/A')}s\n\n---\n\n"

        for section in script_data.get("script_structured", []):
            sec_name = section.get("section", "UNKNOWN")
            script_md += f"## {sec_name}\n\n"
            for line in section.get("lines", []):
                text = line.get("text", "")
                timing = line.get("timing", {})
                start = timing.get("start", 0)
                end = timing.get("end", 0)
                mots = line.get("mots_forts", [])

                # Format timestamp
                def fmt_time(s):
                    m = int(s // 60)
                    sec = int(s % 60)
                    return f"{m:02d}:{sec:02d}"

                script_md += f"**[{fmt_time(start)} → {fmt_time(end)}]** {text}\n"
                if mots:
                    script_md += f"  *Mots forts: {', '.join(mots)}*\n"
                script_md += "\n"

        safe_write(video_dir, "script.md", script_md)

        # script_raw.txt
        raw_path = os.path.join(_F03_OUT, "script_raw.txt")
        if os.path.exists(raw_path):
            safe_copy(raw_path, video_dir, "script_raw.txt")
        else:
            # Generate from structured
            raw = ""
            current_section = ""
            for section in script_data.get("script_structured", []):
                sec = section.get("section", "")
                if sec != current_section:
                    if sec == "Hook" or "ACCROCHE" in sec.upper():
                        raw += "\n[ACCROCHE]\n"
                    elif "CHUTE" in sec.upper() or "CTA" in sec.upper() or "Loop" in sec:
                        raw += "\n[CHUTE/CTA]\n"
                    else:
                        raw += "\n[DÉVELOPPEMENT]\n"
                    current_section = sec
                for line in section.get("lines", []):
                    raw += line.get("text", "") + "\n"
            safe_write(video_dir, "script_raw.txt", raw)

        # timing.json
        timing = script_data.get("timing", {})
        if timing:
            safe_write(video_dir, "timing.json", json.dumps(timing, ensure_ascii=False, indent=2))

        # metadata.md
        meta = script_data.get("metadata", {})
        meta_md = f"""# Métadonnées — {script_data.get('title', 'N/A')}

## Titre
{meta.get('title', script_data.get('title', 'N/A'))}

## Description
{meta.get('description', {}).get('bloc_1_accroche', '')}

{meta.get('description', {}).get('bloc_2_qualite', '')}

{meta.get('description', {}).get('bloc_3_hashtags', '')}

{meta.get('description', {}).get('bloc_4_seo', '')}

## Hashtags
{', '.join(meta.get('hashtags', []))}

## Tags
{', '.join(script_data.get('tags', []))}

## Texte miniature
{script_data.get('thumbnail_text', 'N/A')}
"""
        safe_write(video_dir, "metadata.md", meta_md)

        # metadata.txt (copier-coller direct)
        meta_txt_path = os.path.join(_F03_OUT, "metadata.txt")
        if os.path.exists(meta_txt_path):
            safe_copy(meta_txt_path, video_dir, "metadata.txt")

        print(f"  ✅ {video_dir_name}/ — script.md, script_raw.txt, timing.json, metadata.md")

    # Thumbnail
    thumb_png = os.path.join(_F04_OUT, "thumbnail.png")
    thumb_concept = load_json(os.path.join(_F04_OUT, "thumbnail_concept.json"))

    if safe_copy(thumb_png, video_dir, "thumbnail.png"):
        print(f"  ✅ {video_dir_name}/thumbnail.png")

    if thumb_concept:
        tc = thumb_concept.get("thumbnail_generation", thumb_concept)
        text_info = tc.get("canva_instructions", tc.get("thumbnail_text", "N/A"))
        thumb_text = tc.get("thumbnail_text", "N/A")
        safe_write(video_dir, "thumbnail_texte.md", f"""# Instructions Miniature

## Texte sur la miniature
{thumb_text}

## Instructions Canva
{text_info}

## Visual Skeleton
{json.dumps(thumb_concept.get('visual_skeleton', {}), ensure_ascii=False, indent=2)}
""")
        print(f"  ✅ {video_dir_name}/thumbnail_texte.md")

    return video_dir_name


def export_siege_channel(channel_slug):
    """Export complet Mode Chaîne : CHAÎNE + VIDÉO_001."""
    print(f"\n{'='*60}")
    print(f"EXPORT SIEGE — MODE CHAÎNE")
    print(f"{'='*60}\n")

    # Charger l'identité
    identity_path = os.path.join(_CHANNELS_DIR, channel_slug, "channel_identity.json")
    identity = load_json(identity_path)
    if not identity:
        identity = load_json(os.path.join(_F06_OUT, "channel_identity.json"))
    if not identity:
        print(f"❌ channel_identity.json introuvable pour {channel_slug}")
        return None

    identity["channel_slug"] = channel_slug
    chosen_name = identity.get("chosen_name", channel_slug)

    # Créer le dossier d'export
    export_name = f"EXPORT_{channel_slug}"
    export_dir = os.path.join(_PROJECT_ROOT, export_name)

    # Clean if exists
    if os.path.exists(export_dir):
        shutil.rmtree(export_dir)
    os.makedirs(export_dir)

    print(f"[EXPORT] Dossier: {export_dir}")

    # 1. CHAÎNE/
    print(f"\n[EXPORT] CHAÎNE/")
    name, handle = export_channel_identity(identity, export_dir)

    # 2. VIDÉO_001/
    print(f"\n[EXPORT] VIDÉO_001/")
    video_dir = export_video(1, export_dir)

    # 3. README.md
    print(f"\n[EXPORT] README.md")
    readme = f"""# {chosen_name} — Export Siège #1

## Chaîne
- **Nom**: {name}
- **Handle**: {handle}
- **Niche**: {identity.get('niche', 'N/A')}
- **Concept**: {identity.get('concept', 'N/A')}

## Contenu du dossier

### CHAÎNE/
- `nom.txt` — Nom de la chaîne
- `handle.txt` — Handle YouTube
- `description.md` — Description YouTube (copier-coller)
- `tags.txt` — Tags séparés par virgules
- `tone_of_voice.md` — Référence pour les futurs scripts
- `codes_visuels.md` — Palette, style, template miniature
- `format_standard.md` — Durée, structure, fréquence
- `10_noms_classés.md` — Les 10 noms proposés (référence)
- `banner.png` — Bannière YouTube (upload direct)
- `logo.png` — Logo/avatar (upload direct)

### {video_dir}/
- `script.md` — Script lisible avec timestamps
- `script_raw.txt` — Format META_01 (pour pipeline voix off)
- `timing.json` — Calage visuel (pour SANCTORUM/DORN/CRUSADER)
- `metadata.md` — Titre + description + tags + hashtags
- `thumbnail.png` — Miniature (upload direct)
- `thumbnail_texte.md` — Instructions texte Canva

## Prochaines étapes
1. Créer la chaîne sur YouTube avec le nom, handle, description, tags
2. Uploader le banner et le logo
3. Produire la vidéo avec le script + timing
4. Créer la miniature avec thumbnail.png + instructions Canva
5. Uploader la vidéo avec titre, description, tags
6. Remplir performance.json après publication

## Données techniques
- Export généré: {now_iso()}
- Chaîne enregistrée dans: ARCHIVUM/channels/{channel_slug}/
- Siège #1 complet

*Fer au-dedans, Fer au-dehors.*
"""
    safe_write(export_dir, "README.md", readme)

    # Lister tout
    print(f"\n[EXPORT] Contenu final:")
    for root, dirs, files in os.walk(export_dir):
        level = root.replace(export_dir, "").count(os.sep)
        indent = "  " * level
        print(f"  {indent}{os.path.basename(root)}/")
        for f in sorted(files):
            fpath = os.path.join(root, f)
            size = os.path.getsize(fpath)
            print(f"  {indent}  {f} ({size:,} bytes)")

    print(f"\n✅ Export terminé: {export_dir}")
    return export_dir


def export_siege_video(channel_slug, video_number):
    """Export Mode Vidéo : VIDÉO_NNN uniquement."""
    print(f"\n{'='*60}")
    print(f"EXPORT SIEGE — MODE VIDÉO (#{video_number})")
    print(f"{'='*60}\n")

    export_name = f"EXPORT_video_{video_number:03d}"
    export_dir = os.path.join(_PROJECT_ROOT, export_name)

    if os.path.exists(export_dir):
        shutil.rmtree(export_dir)
    os.makedirs(export_dir)

    print(f"[EXPORT] Dossier: {export_dir}")

    # VIDÉO_NNN/
    video_dir = export_video(video_number, export_dir)

    # README
    safe_write(export_dir, "README.md", f"""# Vidéo #{video_number} — Export

## Contenu
### {video_dir}/
- `script.md` — Script lisible avec timestamps
- `script_raw.txt` — Format META_01 (pour pipeline voix off)
- `timing.json` — Calage visuel
- `metadata.md` — Titre + description + tags
- `thumbnail.png` — Miniature (upload direct)
- `thumbnail_texte.md` — Instructions texte Canva

## Export généré: {now_iso()}
""")

    print(f"\n✅ Export terminé: {export_dir}")
    return export_dir


def main():
    parser = argparse.ArgumentParser(description="Export des artefacts de siège")
    subparsers = parser.add_subparsers(dest="command")

    p_channel = subparsers.add_parser("channel", help="Export Mode Chaîne")
    p_channel.add_argument("--channel-slug", required=True)
    p_channel.set_defaults(func=lambda a: export_siege_channel(a.channel_slug))

    p_video = subparsers.add_parser("video", help="Export Mode Vidéo")
    p_video.add_argument("--channel-slug", required=True)
    p_video.add_argument("--video-number", type=int, required=True)
    p_video.set_defaults(func=lambda a: export_siege_video(a.channel_slug, a.video_number))

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
