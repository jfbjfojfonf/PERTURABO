"""
libs/ledger_manager.py — Gestion du ledger central du forge CLIPPING
====================================================================

Gère liber_clipping.json (état inter-frégates) + délègue les check-in/check-out
à IW_CUSTOS.py à la racine du forge.

Usage (interne à orchestrator.py, pas un CLI autonome):
  from libs.ledger_manager import LedgerManager
  lm = LedgerManager()
  lm.load()
  lm.update(campaign_status="active")
  lm.check_in("F01", "F01_SCOUT/OUT/source_specimen.json")
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_FORGE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_SCRIPT_DIR)))

LIBER_PATH = os.path.join(_FORGE_ROOT, "liber_clipping.json")
IW_CUSTOS_PATH = os.path.join(_FORGE_ROOT, "IW_CUSTOS.py")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class LedgerManager:
    """Point d'accès unique au ledger liber_clipping.json."""

    def __init__(self, liber_path: str = LIBER_PATH):
        self.liber_path = liber_path
        self.data = None

    def load(self) -> dict:
        if not os.path.exists(self.liber_path):
            raise FileNotFoundError(f"liber_clipping.json introuvable: {self.liber_path}")
        with open(self.liber_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        return self.data

    def save(self):
        if self.data is None:
            raise RuntimeError("LedgerManager: charger d'abord le ledger (load)")
        self.data["last_event"] = now_iso()
        with open(self.liber_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def update(self, **kwargs):
        """Met à jour des clés racines du ledger, puis sauvegarde."""
        if self.data is None:
            self.load()
        for key, value in kwargs.items():
            self.data[key] = value
        self.save()

    def set_fregate_status(self, code: str, status: str, output: str = None):
        """Met à jour le statut d'une frégate dans fregates_status."""
        if self.data is None:
            self.load()
        key_map = {
            "F01": "f01_scout", "F02": "f02_tyrant_camp", "F03": "f03_source_hunter",
            "F04": "f04_copywriter", "F05": "f05_packager", "F06": "f06_tracker",
            "TYRANT": "tyrant", "CAPTEURS": "capteurs", "ANGLESMITH": "anglesmith",
        }
        key = key_map.get(code.upper())
        if not key:
            raise ValueError(f"Code frégate inconnu: {code}")
        self.data["fregates_status"][key] = status
        if output:
            self.data["fregates_status"][f"{key}_output"] = output
        self.save()

    def get_fregate_status(self, code: str) -> str:
        if self.data is None:
            self.load()
        key_map = {
            "F01": "f01_scout", "F02": "f02_tyrant_camp", "F03": "f03_source_hunter",
            "F04": "f04_copywriter", "F05": "f05_packager", "F06": "f06_tracker",
            "TYRANT": "tyrant", "CAPTEURS": "capteurs", "ANGLESMITH": "anglesmith",
        }
        key = key_map.get(code.upper())
        return self.data["fregates_status"].get(key, "pending")

    def check_out(self, code: str):
        if os.path.exists(IW_CUSTOS_PATH):
            subprocess.run([sys.executable, IW_CUSTOS_PATH, "--mode", "check-out",
                            "--frigate", code.upper()], capture_output=True, text=True, timeout=30)

    def check_in(self, code: str, output_path: str):
        if os.path.exists(IW_CUSTOS_PATH):
            subprocess.run([sys.executable, IW_CUSTOS_PATH, "--mode", "check-in",
                            "--frigate", code.upper(), "--output", output_path],
                           capture_output=True, text=True, timeout=30)

    def add_porte_validated(self, gate_id: str, decision: str, notes: str = None):
        if self.data is None:
            self.load()
        if decision == "valide":
            self.data.setdefault("portes_validated", [])
            if gate_id not in self.data["portes_validated"]:
                self.data["portes_validated"].append(gate_id)
            next_porte = {"1": "p2", "2": "p3", "3": "p4", "4": "closed"}.get(str(gate_id))
            self.data["current_porte"] = next_porte
        self.data.setdefault("gate_decisions", {})
        self.data["gate_decisions"][f"gate_{gate_id}"] = {
            "validated": decision == "valide",
            "notes": notes,
            "timestamp": now_iso(),
        }
        self.save()

    def append_event(self, event: str, angle_id: str = None):
        if self.data is None:
            self.load()
        self.data.setdefault("log_event", []).append({
            "at": now_iso(), "event": event, "angle_id": angle_id,
        })
        self.save()

    def initialize(self, siege_id: str, directive_path: str, reference_clip_path: str,
                   platform_target: str, market_target: str, n_angles: int,
                   mode: str = None):
        """Réinitialise le ledger pour un nouveau siège (campagne singulière).

        Le profil (mode whop|logo) est PRESERVÉ depuis le liber existant si non
        fourni — fix: --start-siege ne doit plus écraser le profil fixé par
        IW_CUSTOS --init-siege.
        """
        previous_mode = None
        if os.path.exists(self.liber_path):
            try:
                with open(self.liber_path, "r", encoding="utf-8") as f:
                    previous_mode = json.load(f).get("mode")
            except Exception:
                previous_mode = None
        if mode is None:
            mode = previous_mode
        self.data = {
            "siege_id": siege_id,
            "campaign_id": None,
            "campaign_status": "active",
            "current_porte": "init",
            "fleet_status": "pending",
            "mode": mode,
            "inputs_warsmith": {
                "directive_path": directive_path,
                "reference_clip_path": reference_clip_path,
                "platform_target": platform_target,
                "market_target": market_target,
                "n_angles": n_angles,
            },
            "fregates_status": {
                "f01_scout": "pending", "f01_scout_output": None,
                "f02_tyrant_camp": "pending", "f02_tyrant_camp_output": None,
                "anglesmith": "pending", "anglesmith_output": None,
                "f03_source_hunter": "pending", "f03_source_hunter_output": None,
                "f04_copywriter": "pending", "f04_copywriter_output": None,
                "f05_packager": "pending", "f05_packager_output": None,
                "f06_tracker": "pending", "f06_tracker_output": None,
                "tyrant": "pending", "tyrant_output": None,
                "capteurs": "pending", "capteurs_output": None,
            },
            "portes_validated": [],
            "gate_decisions": {},
            "packs_expedies_count": 0,
            "packs_posted_count": 0,
            "packs_submitted_whop_count": 0,
            "last_event": "siege_started",
            "siege_started_at": now_iso(),
            "siege_closed_at": None,
            "log_event": [{"at": now_iso(), "event": "siege_started", "angle_id": None}],
            "iw_custos": {"last_validation": None, "errors": []},
        }
        self.save()
        return self.data
