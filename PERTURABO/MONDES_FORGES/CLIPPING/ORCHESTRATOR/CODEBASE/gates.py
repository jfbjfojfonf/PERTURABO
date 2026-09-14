"""
gates.py — Les Quatre Portes du Forge CLIPPING
===============================================

Moments de souveraineté humaine. L'IRON s'arrête à chaque porte.
Le Warsmith décide. L'Orchestrateur enregistre.

Porte 1 — Le Verdict  : F01_SCOUT + F02_TYRANT_CAMP → verdict GO/NO-GO + océan bleu.
Porte 2 — Les Angles  : ANGLESMITH forge les N angles d'attaque.
Porte 3 — Les Textes  : F03_SOURCE_HUNTER + F04_COPYWRITER → specimens + text_payloads.
Porte 4 — Les Packs   : F05_PACKAGER assemble les N production_packs → OMNIS_WATCH.
"""

import json
import os
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Porte:
    """Représente une porte de souveraineté."""

    def __init__(self, gate_id: str, nom: str, description: str, fregates: list[str]):
        self.gate_id = gate_id
        self.nom = nom
        self.description = description
        self.fregates = fregates
        self.statut = "VERROUILLEE"
        self.decision = None
        self.notes = None
        self.timestamp = None

    def ouvrir(self):
        self.statut = "EN_ATTENTE"
        print(f"\n{'═' * 60}")
        print(f" PORTE {self.gate_id} — {self.nom}")
        print(f"{'═' * 60}")
        print(f"{self.description}")
        print(f"Frégates mobilisées : {', '.join(self.fregates)}")
        print(f"{'═' * 60}\n")

    def valider(self, notes: str = None):
        self.statut = "VALIDEE"
        self.decision = "valide"
        self.notes = notes
        self.timestamp = now_iso()
        print(f"[PORTE {self.gate_id}]  Validée par le Warsmith")

    def rejeter(self, notes: str = None):
        self.statut = "REJETEE"
        self.decision = "rejete"
        self.notes = notes
        self.timestamp = now_iso()
        print(f"[PORTE {self.gate_id}]  Rejetée par le Warsmith")
        if notes:
            print(f"[PORTE {self.gate_id}] Notes: {notes}")

    def to_dict(self) -> dict:
        return {
            "nom": self.nom,
            "description": self.description,
            "fregates": self.fregates,
            "statut": self.statut,
            "decision": self.decision,
            "notes": self.notes,
            "timestamp": self.timestamp,
        }


PORTES = {
    "PORTE_1_VERDICT": Porte(
        "1", "Le Verdict",
        "F01_SCOUT inventorie les assets de la campagne. F02_TYRANT_CAMP rend le verdict "
        "GO/NO-GO + identification de l'océan bleu (1 couche max, même source).\n"
        "Le Warsmith valide ou rejette le verdict. NO-GO = campagne non poursuivie.",
        ["F01_SCOUT", "F02_TYRANT_CAMP"],
    ),
    "PORTE_2_ANGLES": Porte(
        "2", "Les Angles",
        "ANGLESMITH forge les N angles d'attaque (direct + océan bleu) avec 4 axes "
        "(angle_family, emotion_mode, engagement_type, reframe_dim) et la règle anti-cannibale.\n"
        "Le Warsmith valide ou tue des angles (re-forge si kill).",
        ["ANGLESMITH"],
    ),
    "PORTE_3_TEXTES": Porte(
        "3", "Les Textes",
        "F03_SOURCE_HUNTER sélectionne asset + segments par angle. "
        "F04_COPYWRITER forge les text_payloads (3 titres + paragraphe + caption + hashtags).\n"
        "Le Warsmith + l'IRON ordonnancement valident les N text_payloads.",
        ["F03_SOURCE_HUNTER", "F04_COPYWRITER"],
    ),
    "PORTE_4_PACKS": Porte(
        "4", "Les Packs",
        "F05_PACKAGER assemble les N production_pack.json (contrat OMNIS_WATCH).\n"
        "Si validé : packs expédiés à OMNIS_WATCH (raw URL), F06_TRACKER prend le relais.",
        ["F05_PACKAGER"],
    ),
}

ORDRE_PORTES = ["PORTE_1_VERDICT", "PORTE_2_ANGLES", "PORTE_3_TEXTES", "PORTE_4_PACKS"]

_KEY_BY_ID = {"1": "PORTE_1_VERDICT", "2": "PORTE_2_ANGLES",
              "3": "PORTE_3_TEXTES", "4": "PORTE_4_PACKS"}


def ouvrir_porte(gate_id: str):
    key = _KEY_BY_ID.get(str(gate_id))
    if key not in PORTES:
        raise ValueError(f"Porte inconnue: {gate_id}")
    PORTES[key].ouvrir()


def valider_porte(gate_id: str, notes: str = None):
    key = _KEY_BY_ID.get(str(gate_id))
    if key not in PORTES:
        raise ValueError(f"Porte inconnue: {gate_id}")
    PORTES[key].valider(notes)


def rejeter_porte(gate_id: str, notes: str = None):
    key = _KEY_BY_ID.get(str(gate_id))
    if key not in PORTES:
        raise ValueError(f"Porte inconnue: {gate_id}")
    PORTES[key].rejeter(notes)


def porte_suivante(gate_id_actuelle: str) -> str | None:
    if gate_id_actuelle is None:
        return "1"
    idx = int(gate_id_actuelle)
    if idx + 1 <= 4:
        return str(idx + 1)
    return None


def portes_to_dict() -> dict:
    return {gid: porte.to_dict() for gid, porte in PORTES.items()}


def reset_portes():
    for porte in PORTES.values():
        porte.statut = "VERROUILLEE"
        porte.decision = None
        porte.notes = None
        porte.timestamp = None
