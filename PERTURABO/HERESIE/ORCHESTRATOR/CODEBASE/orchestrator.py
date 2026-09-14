"""
orchestrator.py — L'Orchestrateur : Le Nerf Central
=====================================================

Coordonne le flux complet de PERTURABO entre les quatre portes.
Gère les deux modes : Vidéo et Chaîne.

Flux Mode Vidéo :
  [Porte 1] → TYRANT → SENTINEL → BREACHER → [Porte 2] → FORGEWARD → HERALD → [Porte 3] → [Porte 4]

Flux Mode Chaîne :
  [Porte 1] → TYRANT → SENTINEL → GRAND_COMPASS → IDENTITY_FORGE → [Porte 2] → FORGEWARD → [Porte 3] → [Porte 4]

Usage:
  python orchestrator.py --mode video --url "https://..." --niche "..." --format SHORT --duree 60
  python orchestrator.py --mode channel --url "https://..."
  python orchestrator.py --resume
  python orchestrator.py --status
"""

import argparse
import json
import os
import sys
import shutil
from datetime import datetime, timezone

# Path anchoring
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_ORCH_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_ORCH_DIR)

# Import gates
sys.path.insert(0, _SCRIPT_DIR)
from gates import PORTES, ORDRE_PORTES, ouvrir_porte, valider_porte, rejeter_porte, porte_suivante, portes_to_dict, reset_portes

# Paths
_ARCHIVUM_LEDGERS = os.path.join(_PROJECT_ROOT, "ARCHIVUM", "ledgers")
_ARCHIVUM_TEMPLATES = os.path.join(_PROJECT_ROOT, "ARCHIVUM", "templates")
_SHARED_OUT = os.path.join(_PROJECT_ROOT, "SHARED", "OUT")

# Frégate paths
_FREGATES = {
    "TYRANT": {"in": os.path.join(_PROJECT_ROOT, "TYRANT", "IN"),
               "out": os.path.join(_PROJECT_ROOT, "TYRANT", "OUT")},
    "F01": {"in": os.path.join(_PROJECT_ROOT, "F01_SENTINEL", "IN"),
            "out": os.path.join(_PROJECT_ROOT, "F01_SENTINEL", "OUT")},
    "F02": {"in": os.path.join(_PROJECT_ROOT, "F02_BREACHER", "IN"),
            "out": os.path.join(_PROJECT_ROOT, "F02_BREACHER", "OUT")},
    "F03": {"in": os.path.join(_PROJECT_ROOT, "F03_FORGEWARD", "IN"),
            "out": os.path.join(_PROJECT_ROOT, "F03_FORGEWARD", "OUT")},
    "F04": {"in": os.path.join(_PROJECT_ROOT, "F04_HERALD", "IN"),
            "out": os.path.join(_PROJECT_ROOT, "F04_HERALD", "OUT")},
    "F05": {"in": os.path.join(_PROJECT_ROOT, "F05_GRAND_COMPASS", "IN"),
            "out": os.path.join(_PROJECT_ROOT, "F05_GRAND_COMPASS", "OUT")},
    "F06": {"in": os.path.join(_PROJECT_ROOT, "F06_IDENTITY_FORGE", "IN"),
            "out": os.path.join(_PROJECT_ROOT, "F06_IDENTITY_FORGE", "OUT")},
    "S01": {"in": os.path.join(_PROJECT_ROOT, "S01_SENTINEL", "IN"),
            "out": os.path.join(_PROJECT_ROOT, "S01_SENTINEL", "OUT")},
    "S02": {"in": os.path.join(_PROJECT_ROOT, "S02_BREACHER", "IN"),
            "out": os.path.join(_PROJECT_ROOT, "S02_BREACHER", "OUT")},
    "S03": {"in": os.path.join(_PROJECT_ROOT, "S03_FORGEWARD", "IN"),
            "out": os.path.join(_PROJECT_ROOT, "S03_FORGEWARD", "OUT")},
    "S04": {"in": os.path.join(_PROJECT_ROOT, "S04_HERALD", "IN"),
            "out": os.path.join(_PROJECT_ROOT, "S04_HERALD", "OUT")},
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_siege_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"perturabo_{ts}"


def create_ledger(siege_id: str, mode: str, url: str, niche: str,
                  fmt: str, duree: int, intent: str) -> dict:
    """Crée un nouveau Grand Company Ledger pour le siège."""
    ledger = {
        "siege_id": siege_id,
        "mode": mode,
        "status": "gate_1",
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "warsmith_brief": {
            "video_url": url,
            "niche": niche,
            "format": fmt,
            "duree": duree,
            "intent": intent,
        },
        "tyrant_report": None,
        "f01_sentinel": None,
        "f02_breacher": None,
        "f03_forgeward": None,
        "f04_herald": None,
        "f05_grand_compass": None,
        "f06_identity_forge": None,
        "gate_decisions": {},
        "final_output": None,
    }
    save_ledger(ledger)
    return ledger


def save_ledger(ledger: dict):
    """Sauvegarde le ledger dans ARCHIVUM/ledgers/."""
    os.makedirs(_ARCHIVUM_LEDGERS, exist_ok=True)
    ledger["updated_at"] = now_iso()
    path = os.path.join(_ARCHIVUM_LEDGERS, f"{ledger['siege_id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, ensure_ascii=False, indent=2)


def load_ledger(siege_id: str) -> dict:
    """Charge un ledger depuis ARCHIVUM/ledgers/."""
    path = os.path.join(_ARCHIVUM_LEDGERS, f"{siege_id}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Ledger introuvable: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_latest_ledger() -> str | None:
    """Trouve le ledger le plus récent."""
    if not os.path.exists(_ARCHIVUM_LEDGERS):
        return None
    files = sorted([f for f in os.listdir(_ARCHIVUM_LEDGERS) if f.endswith(".json")], reverse=True)
    if not files:
        return None
    return files[0].replace(".json", "")


def move_file(src: str, dest_dir: str, dest_name: str = None):
    """Déplace un fichier d'une frégate OUT/ vers la frégate IN/ suivante."""
    if not os.path.exists(src):
        print(f"[ORCH] ⚠️ Fichier source introuvable: {src}")
        return False
    os.makedirs(dest_dir, exist_ok=True)
    if dest_name is None:
        dest_name = os.path.basename(src)
    dest = os.path.join(dest_dir, dest_name)
    shutil.copy2(src, dest)
    print(f"[ORCH] 📦 Transfert: {src} → {dest}")
    return True


def present_gate(gate_num: str, ledger: dict):
    """Présente une porte au Warsmith avec le contenu à valider."""
    ouvrir_porte(gate_num)

    if gate_num == "1":
        # Porte 1 : afficher le rapport du TYRANT
        if ledger.get("tyrant_report"):
            report = ledger["tyrant_report"]
            print(f"📋 Rapport d'Éclairement du TYRANT :")
            print(f"   Territoire : {report.get('territory_analysis', {}).get('taille', 'N/A')}")
            print(f"   Démon : {report.get('demon_identification', {}).get('who', 'N/A')}")
            print(f"   Chemin recommandé : {report.get('recommended_path', 'N/A')}")
            print(f"   Automatisabilité : {report.get('automatability_score', 'N/A')}/10")
            print(f"   Hunt brief : {report.get('hunt_brief', 'N/A')[:100]}...")

    elif gate_num == "2":
        # Porte 2 : afficher le squelette (Mode Vidéo) ou le rapport de niche (Mode Chaîne)
        if ledger["mode"] == "video":
            if ledger.get("f02_breacher"):
                skel = ledger["f02_breacher"].get("skeleton", {})
                print(f"📋 Squelette viral extrait par BREACHER :")
                for section in ["Hook", "Promise", "Rehook_1", "Rehook_2", "Body_Structure", "Payoff", "CTA"]:
                    if section in skel:
                        el = skel[section]
                        phrase = el.get("phrase_exacte", el.get("type_structure", el.get("type_cta", "N/A")))
                        print(f"   {section} : {phrase[:80] if isinstance(phrase, str) else 'N/A'}")
        elif ledger["mode"] == "channel":
            if ledger.get("f05_grand_compass"):
                report = ledger["f05_grand_compass"]
                print(f"📋 Rapport de territoire de GRAND_COMPASS :")
                print(f"   Concept : {report.get('concept_identified', 'N/A')}")
                print(f"   Niche recommandée : {report.get('recommended_niche', 'N/A')}")
                for v in report.get("blue_ocean_validations", [])[:3]:
                    print(f"   → {v['niche']} : {v['verdict']} (confiance: {v.get('confidence_score', 'N/A')}/10)")
            if ledger.get("f06_identity_forge"):
                identity = ledger["f06_identity_forge"]
                print(f"\n📋 Identité de chaîne forgée par IDENTITY_FORGE :")
                names = identity.get("channel_names", [])
                for n in names[:5]:
                    print(f"   #{n.get('rank', '?')}: {n.get('name', 'N/A')} (mem: {n.get('memorability_score', '?')}/10, seo: {n.get('seo_score', '?')}/10)")
                tov = identity.get("tone_of_voice", {})
                print(f"   Tone : {tov.get('register', 'N/A')}")
                print(f"   Format : {identity.get('format_standard', {}).get('structure', 'N/A')}")
                print(f"   Banner : {'✅' if os.path.exists(os.path.join(_FREGATES['F06']['out'], 'banner.png')) else '❌'}")
                print(f"   Logo   : {'✅' if os.path.exists(os.path.join(_FREGATES['F06']['out'], 'logo.png')) else '❌'}")

    elif gate_num == "3":
        # Porte 3 : afficher le script
        if ledger.get("f03_forgeward"):
            script = ledger["f03_forgeward"]
            print(f"📋 Script généré par FORGEWARD :")
            print(f"   Titre : {script.get('metadata', {}).get('title', 'N/A')}")
            print(f"   Format : {script.get('format', 'N/A')} — Durée : {script.get('duree_cible', 'N/A')}s")
            sections = [s.get("section", "") for s in script.get("script_structured", [])]
            print(f"   Sections : {sections}")
            print(f"   Segments timing : {len(script.get('timing', {}).get('segments', []))}")
            print(f"   Thumbnail text : {script.get('thumbnail_text', 'N/A')}")

    elif gate_num == "4":
        # Porte 4 : afficher l'artefact final
        print(f"📋 Artefact final :")
        if ledger["mode"] == "video":
            print(f"   Script : {ledger.get('f03_forgeward', {}).get('metadata', {}).get('title', 'N/A')}")
            print(f"   Miniature : {'✅ générée' if ledger.get('f04_herald') else '❌ absente'}")
            if ledger.get("f04_herald"):
                print(f"   Texte miniature : {ledger['f04_herald'].get('thumbnail_text', 'N/A')}")
        elif ledger["mode"] == "channel":
            print(f"   Rapport de niche : {ledger.get('f05_grand_compass', {}).get('recommended_niche', 'N/A')}")
            print(f"   Premier script : {ledger.get('f03_forgeward', {}).get('metadata', {}).get('title', 'N/A')}")

    print(f"\n{'─' * 60}")
    print(f"Le Warsmith doit décider :")
    print(f"  → Valider : python orchestrator.py --gate {gate_num} --decision valide")
    print(f"  → Rejeter : python orchestrator.py --gate {gate_num} --decision rejete --notes \"...\"")
    print(f"{'─' * 60}\n")


def run_video_mode(url: str, niche: str, fmt: str, duree: int, intent: str):
    """
    Flux Mode Vidéo :
    [Porte 1] → TYRANT → SENTINEL → BREACHER → [Porte 2] → FORGEWARD → HERALD → [Porte 3] → [Porte 4]
    """
    siege_id = generate_siege_id()
    print(f"\n{'╔' + '═'*58 + '╗'}")
    print(f"║  PERTURABO — SIÈGE {siege_id} — MODE VIDÉO{' '*(28-len(siege_id))}║")
    print(f"{'╚' + '═'*58 + '╝'}\n")

    # Créer le ledger
    ledger = create_ledger(siege_id, "video", url, niche, fmt, duree, intent)
    print(f"[ORCH] Ledger créé : {siege_id}")

    # === PORTE 1 : BRIEF ===
    print(f"\n[ORCH] Phase 1 : TYRANT — Éclairement du territoire...")
    # Le TYRANT prépare son prompt (l'Orchestrateur écrit le brief)
    brief_path = os.path.join(_FREGATES["TYRANT"]["in"], "brief.json")
    with open(brief_path, "w", encoding="utf-8") as f:
        json.dump({"video_url": url, "niche": niche, "intent": intent}, f, ensure_ascii=False, indent=2)

    print(f"[ORCH] Brief écrit pour TYRANT : {brief_path}")
    print(f"[ORCH] ⚠️ Le TYRANT doit être activé manuellement :")
    print(f"  cd TYRANT/CODEBASE && python tyrant.py --prepare --brief ../IN/brief.json")
    print(f"  # L'IRON (Claude) produit eclairissement.json")
    print(f"  python tyrant.py --finalize")
    print(f"\n[ORCH] Ensuite, reprendre : python orchestrator.py --resume")

    # Présenter la Porte 1
    present_gate("1", ledger)

    # Sauvegarder le ledger
    save_ledger(ledger)
    print(f"\n[ORCH] Siège en attente à la Porte 1. Ledger : {siege_id}")


def run_channel_mode(url: str, intent: str):
    """
    Flux Mode Chaîne :
    [Porte 1] → TYRANT → SENTINEL → GRAND_COMPASS → [Porte 2] → FORGEWARD → [Porte 3] → [Porte 4]
    """
    siege_id = generate_siege_id()
    print(f"\n{'╔' + '═'*58 + '╗'}")
    print(f"║  PERTURABO — SIÈGE {siege_id} — MODE CHAÎNE{' '*(27-len(siege_id))}║")
    print(f"{'╚' + '═'*58 + '╝'}\n")

    # Créer le ledger
    ledger = create_ledger(siege_id, "channel", url, "", "", 0, intent)
    print(f"[ORCH] Ledger créé : {siege_id}")

    # === PORTE 1 : BRIEF ===
    print(f"\n[ORCH] Phase 1 : TYRANT — Éclairement du territoire...")
    brief_path = os.path.join(_FREGATES["TYRANT"]["in"], "brief.json")
    with open(brief_path, "w", encoding="utf-8") as f:
        json.dump({"video_url": url, "niche": "", "intent": intent}, f, ensure_ascii=False, indent=2)

    print(f"[ORCH] Brief écrit pour TYRANT : {brief_path}")
    print(f"[ORCH] ⚠️ Le TYRANT doit être activé manuellement :")
    print(f"  cd TYRANT/CODEBASE && python tyrant.py --prepare --brief ../IN/brief.json")
    print(f"  # L'IRON (Claude) produit eclairissement.json")
    print(f"  python tyrant.py --finalize")
    print(f"\n[ORCH] Ensuite, reprendre : python orchestrator.py --resume")

    # Présenter la Porte 1
    present_gate("1", ledger)

    save_ledger(ledger)
    print(f"\n[ORCH] Siège en attente à la Porte 1. Ledger : {siege_id}")


def resume_siege():
    """Reprend un siège en cours depuis le ledger."""
    siege_id = find_latest_ledger()
    if not siege_id:
        print("[ORCH] ❌ Aucun ledger trouvé. Lance un nouveau siège.")
        return

    ledger = load_ledger(siege_id)
    status = ledger.get("status", "gate_1")
    mode = ledger.get("mode", "video")

    print(f"\n[ORCH] Reprise du siège : {siege_id}")
    print(f"[ORCH] Mode : {mode} — Statut : {status}")

    # Déterminer où on en est et continuer
    if status == "gate_1":
        # Vérifier si le TYRANT a produit son rapport
        tyrant_out = os.path.join(_FREGATES["TYRANT"]["out"], "eclairissement.json")
        if os.path.exists(tyrant_out):
            with open(tyrant_out, "r", encoding="utf-8") as f:
                ledger["tyrant_report"] = json.load(f)
            save_ledger(ledger)
            print(f"[ORCH] ✅ Rapport du TYRANT chargé")
            present_gate("1", ledger)
        else:
            print(f"[ORCH] ⚠️ TYRANT n'a pas encore produit eclairissement.json")
            print(f"  Lancer : cd TYRANT/CODEBASE && python tyrant.py --prepare --brief ../IN/brief.json")

    elif status == "gate_2":
        # Après Porte 1 validée → lancer SENTINEL + BREACHER (ou GRAND_COMPASS)
        print(f"[ORCH] Porte 1 validée. Lancement des frégates...")

        # Transférer le brief vers SENTINEL
        brief = ledger["warsmith_brief"]
        sentinel_brief = os.path.join(_FREGATES["F01"]["in"], "brief.json")
        with open(sentinel_brief, "w", encoding="utf-8") as f:
            json.dump({"video_url": brief["video_url"], "niche": brief.get("niche", "")}, f, ensure_ascii=False, indent=2)

        print(f"[ORCH] ⚠️ SENTINEL doit être activée :")
        print(f"  cd F01_SENTINEL/CODEBASE && python sentinel.py --url \"{brief['video_url']}\"")
        print(f"\n[ORCH] Ensuite, l'Orchestrateur transfère specimen.json vers la frégate suivante.")

        if mode == "video":
            print(f"\n[ORCH] Après SENTINEL → BREACHER :")
            print(f"  cp F01_SENTINEL/OUT/specimen.json F02_BREACHER/IN/")
            print(f"  cd F02_BREACHER/CODEBASE && python breacher.py --prepare")
            print(f"  # L'IRON produit skeleton.json")
            print(f"  python breacher.py --finalize")
        elif mode == "channel":
            print(f"\n[ORCH] Après SENTINEL → GRAND_COMPASS :")
            print(f"  cp F01_SENTINEL/OUT/specimen.json F05_GRAND_COMPASS/IN/")
            print(f"  cd F05_GRAND_COMPASS/CODEBASE && python grand_compass.py --prepare")
            print(f"  # L'IRON produit niche_report.json")
            print(f"  python grand_compass.py --finalize")
            print(f"\n[ORCH] Après GRAND_COMPASS → IDENTITY_FORGE :")
            print(f"  cp F05_GRAND_COMPASS/OUT/niche_report.json F06_IDENTITY_FORGE/IN/")
            print(f"  cp F01_SENTINEL/OUT/specimen.json F06_IDENTITY_FORGE/IN/")
            print(f"  cd F06_IDENTITY_FORGE/CODEBASE && python identity_forge.py --prepare --niche \"<niche>\"")
            print(f"  # L'IRON produit channel_identity.json + banner.png + logo.png")
            print(f"  python identity_forge.py --finalize")
            print(f"  # Warsmith choisit le nom puis :")
            print(f"  python identity_forge.py --register --channel-name \"Nom Choisi\"")

        # Charger les outputs si disponibles
        specimen_path = os.path.join(_FREGATES["F01"]["out"], "specimen.json")
        if os.path.exists(specimen_path):
            with open(specimen_path, "r", encoding="utf-8") as f:
                ledger["f01_sentinel"] = json.load(f)

        if mode == "video":
            skeleton_path = os.path.join(_FREGATES["F02"]["out"], "skeleton.json")
            if os.path.exists(skeleton_path):
                with open(skeleton_path, "r", encoding="utf-8") as f:
                    ledger["f02_breacher"] = json.load(f)
                save_ledger(ledger)
                present_gate("2", ledger)
        elif mode == "channel":
            report_path = os.path.join(_FREGATES["F05"]["out"], "niche_report.json")
            if os.path.exists(report_path):
                with open(report_path, "r", encoding="utf-8") as f:
                    ledger["f05_grand_compass"] = json.load(f)
                save_ledger(ledger)

            # Charger F06_IDENTITY_FORGE si disponible
            identity_path = os.path.join(_FREGATES["F06"]["out"], "channel_identity.json")
            if os.path.exists(identity_path):
                with open(identity_path, "r", encoding="utf-8") as f:
                    ledger["f06_identity_forge"] = json.load(f)
                save_ledger(ledger)

            present_gate("2", ledger)

        save_ledger(ledger)

    elif status == "gate_3":
        # Après Porte 2 validée → lancer FORGEWARD (+ HERALD pour Mode Vidéo)
        print(f"[ORCH] Porte 2 validée. Lancement de FORGEWARD...")

        brief = ledger["warsmith_brief"]
        niche = brief.get("niche", "")
        if mode == "channel" and ledger.get("f05_grand_compass"):
            niche = ledger["f05_grand_compass"].get("recommended_niche", niche)

        # Transférer skeleton vers FORGEWARD
        if ledger.get("f02_breacher"):
            skeleton_path = os.path.join(_FREGATES["F02"]["out"], "skeleton.json")
            dest = os.path.join(_FREGATES["F03"]["in"], "skeleton.json")
            move_file(skeleton_path, _FREGATES["F03"]["in"], "skeleton.json")

        # Écrire le brief pour FORGEWARD
        f03_brief = os.path.join(_FREGATES["F03"]["in"], "brief.json")
        with open(f03_brief, "w", encoding="utf-8") as f:
            json.dump({"niche": niche, "format": brief.get("format", "SHORT"),
                       "duree": brief.get("duree", 60)}, f, ensure_ascii=False, indent=2)

        print(f"[ORCH] ⚠️ FORGEWARD doit être activé :")
        print(f"  cd F03_FORGEWARD/CODEBASE && python forgeward.py --prepare --niche \"{niche}\" --format {brief.get('format', 'SHORT')} --duree {brief.get('duree', 60)}")
        print(f"  # L'IRON produit script.json")
        print(f"  python forgeward.py --finalize")

        if mode == "video":
            print(f"\n[ORCH] Après FORGEWARD → HERALD :")
            print(f"  cp F01_SENTINEL/OUT/specimen.json F04_HERALD/IN/")
            print(f"  cp F03_FORGEWARD/OUT/script.json F04_HERALD/IN/brief.json (extraire titre + niche)")
            print(f"  cd F04_HERALD/CODEBASE && python herald.py --prepare")
            print(f"  # L'IRON produit thumbnail_concept.json + thumbnail.png")
            print(f"  python herald.py --finalize")

        # Charger les outputs si disponibles
        script_path = os.path.join(_FREGATES["F03"]["out"], "script.json")
        if os.path.exists(script_path):
            with open(script_path, "r", encoding="utf-8") as f:
                ledger["f03_forgeward"] = json.load(f)
            save_ledger(ledger)
            present_gate("3", ledger)

        if mode == "video":
            herald_path = os.path.join(_FREGATES["F04"]["out"], "thumbnail_concept.json")
            if os.path.exists(herald_path):
                with open(herald_path, "r", encoding="utf-8") as f:
                    ledger["f04_herald"] = json.load(f)
                save_ledger(ledger)

        save_ledger(ledger)

    elif status == "gate_4":
        # Présenter l'artefact final
        present_gate("4", ledger)

    elif status == "completed":
        print(f"[ORCH] ✅ Siège {siege_id} déjà terminé.")

    save_ledger(ledger)


def cmd_gate(args):
    """Enregistre la décision du Warsmith à une porte."""
    siege_id = find_latest_ledger()
    if not siege_id:
        print("[ORCH] ❌ Aucun siège en cours.")
        return

    ledger = load_ledger(siege_id)
    gate_num = args.gate
    decision = args.decision
    notes = args.notes

    if decision == "valide":
        valider_porte(gate_num, notes)
        ledger["gate_decisions"][f"gate_{gate_num}"] = {
            "validated": True, "timestamp": now_iso(), "notes": notes
        }

        # Avancer le statut
        if gate_num == "1":
            ledger["status"] = "gate_2"
        elif gate_num == "2":
            ledger["status"] = "gate_3"
        elif gate_num == "3":
            ledger["status"] = "gate_4"
        elif gate_num == "4":
            # Siège terminé — sauvegarder l'artefact
            ledger["status"] = "completed"
            os.makedirs(_SHARED_OUT, exist_ok=True)
            os.makedirs(_ARCHIVUM_TEMPLATES, exist_ok=True)

            # Copier les artefacts vers SHARED/OUT et ARCHIVUM/templates
            if ledger.get("f03_forgeward"):
                src = os.path.join(_FREGATES["F03"]["out"], "script.json")
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(_SHARED_OUT, "script.json"))
                    shutil.copy2(src, os.path.join(_ARCHIVUM_TEMPLATES, f"{siege_id}_script.json"))

            if ledger.get("f04_herald"):
                src = os.path.join(_FREGATES["F04"]["out"], "thumbnail_concept.json")
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(_SHARED_OUT, "thumbnail_concept.json"))
                    shutil.copy2(src, os.path.join(_ARCHIVUM_TEMPLATES, f"{siege_id}_thumbnail.json"))

            print(f"[ORCH] 🏆 Artefact sauvegardé dans SHARED/OUT/ et ARCHIVUM/templates/")

    elif decision == "rejete":
        rejeter_porte(gate_num, notes)
        ledger["gate_decisions"][f"gate_{gate_num}"] = {
            "validated": False, "timestamp": now_iso(), "notes": notes
        }
        print(f"[ORCH] ⚠️ Porte {gate_num} rejetée. Notes: {notes}")
        print(f"[ORCH] La frégate concernée doit être relancée avec les notes du Warsmith.")

    save_ledger(ledger)
    print(f"[ORCH] Ledger mis à jour : {siege_id}")


def cmd_status(args):
    """Affiche l'état du siège en cours."""
    siege_id = find_latest_ledger()
    if not siege_id:
        print("[ORCH] Aucun siège en cours.")
        return

    ledger = load_ledger(siege_id)
    print(f"\n{'╔' + '═'*58 + '╗'}")
    print(f"║  PERTURABO — ÉTAT DU SIÈGE{' '*(33)}║")
    print(f"{'╠' + '═'*58 + '╣'}")
    print(f"║  Siege ID    : {siege_id:<37}║")
    print(f"║  Mode        : {ledger.get('mode', 'N/A'):<37}║")
    print(f"║  Statut      : {ledger.get('status', 'N/A'):<37}║")
    print(f"║  TYRANT      : {'✅' if ledger.get('tyrant_report') else '❌':<37}║")
    print(f"║  F01 SENTINEL: {'✅' if ledger.get('f01_sentinel') else '❌':<37}║")
    print(f"║  F02 BREACHER: {'✅' if ledger.get('f02_breacher') else '❌':<37}║")
    print(f"║  F03 FORGEWARD:{'✅' if ledger.get('f03_forgeward') else '❌':<37}║")
    print(f"║  F04 HERALD  : {'✅' if ledger.get('f04_herald') else '❌':<37}║")
    print(f"║  F05 COMPASS : {'✅' if ledger.get('f05_grand_compass') else '❌':<37}║")
    print(f"║  F06 IDENTITY:{'✅' if ledger.get('f06_identity_forge') else '❌':<37}║")
    decisions = ledger.get("gate_decisions", {})
    for g in ["1", "2", "3", "4"]:
        d = decisions.get(f"gate_{g}", {})
        status = "✅" if d.get("validated") else "❌" if d.get("validated") is False else "⏳"
        print(f"║  Porte {g}      : {status:<37}║")
    print(f"{'╚' + '═'*58 + '╝'}")


def main():
    parser = argparse.ArgumentParser(description="PERTURABO — L'Orchestrateur")
    subparsers = parser.add_subparsers(dest="command", help="Commande")

    # start
    p_start = subparsers.add_parser("start", help="Lancer un nouveau siège")
    p_start.add_argument("--mode", required=True, choices=["video", "channel"])
    p_start.add_argument("--url", required=True, help="URL YouTube cible")
    p_start.add_argument("--niche", default="", help="Niche de destination (Mode Vidéo)")
    p_start.add_argument("--format", default="SHORT", choices=["SHORT", "LONG"])
    p_start.add_argument("--duree", type=int, default=60)
    p_start.add_argument("--intent", default="", help="Intention du Warsmith")
    p_start.set_defaults(func=lambda a: run_video_mode(a.url, a.niche, a.format, a.duree, a.intent) if a.mode == "video" else run_channel_mode(a.url, a.intent))

    # resume
    p_resume = subparsers.add_parser("resume", help="Reprendre le siège en cours")
    p_resume.set_defaults(func=lambda a: resume_siege())

    # gate
    p_gate = subparsers.add_parser("gate", help="Décision du Warsmith à une porte")
    p_gate.add_argument("--gate", required=True, choices=["1", "2", "3", "4"])
    p_gate.add_argument("--decision", required=True, choices=["valide", "rejete"])
    p_gate.add_argument("--notes", default=None)
    p_gate.set_defaults(func=cmd_gate)

    # status
    p_status = subparsers.add_parser("status", help="État du siège")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
