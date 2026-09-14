"""
gates.py — Les Quatre Portes de Siège
======================================

Moments de souveraineté humaine. L'IRON s'arrête à chaque porte.
Le Warsmith décide. L'Orchestrateur enregistre.

Porte 1 — Le Brief     : Warsmith fournit URL + niche. TYRANT éclaire.
Porte 2 — Le Specimen  : Warsmith valide le squelette (Mode Vidéo) ou le territoire (Mode Chaîne).
Porte 3 — Le Blueprint : Warsmith valide le script généré.
Porte 4 — L'Artefact   : Warsmith valide l'artefact final pour publication.
"""

import json
import os
import sys
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Porte:
    """Représente une porte de souveraineté."""

    def __init__(self, gate_id: str, nom: str, description: str):
        self.gate_id = gate_id
        self.nom = nom
        self.description = description
        self.statut = "VERROUILLEE"
        self.inputs = {}
        self.decision = None
        self.notes = None
        self.timestamp = None

    def ouvrir(self):
        """Ouvre la porte — l'IRON s'arrête et attend le Warsmith."""
        self.statut = "EN_ATTENTE"
        print(f"\n{'═' * 60}")
        print(f"🚪 PORTE {self.gate_id} — {self.nom}")
        print(f"{'═' * 60}")
        print(f"{self.description}")
        print(f"{'═' * 60}\n")

    def valider(self, notes: str = None):
        """Le Warsmith valide la porte."""
        self.statut = "VALIDEE"
        self.decision = "valide"
        self.notes = notes
        self.timestamp = now_iso()
        print(f"[PORTE {self.gate_id}] ✅ Validée par le Warsmith")

    def rejeter(self, notes: str = None):
        """Le Warsmith rejette la porte — demande une itération."""
        self.statut = "REJETEE"
        self.decision = "rejete"
        self.notes = notes
        self.timestamp = now_iso()
        print(f"[PORTE {self.gate_id}] ❌ Rejetée par le Warsmith")
        if notes:
            print(f"[PORTE {self.gate_id}] Notes: {notes}")

    def to_dict(self) -> dict:
        return {
            "nom": self.nom,
            "description": self.description,
            "statut": self.statut,
            "decision": self.decision,
            "notes": self.notes,
            "timestamp": self.timestamp,
        }


# Les quatre portes doctrinales
PORTES = {
    "PORTE_1_BRIEF": Porte(
        "1", "Le Brief",
        "Le Warsmith fournit l'URL cible + la niche/intention.\n"
        "Le TYRANT éclaire le territoire avant le siège.\n"
        "L'Orchestrateur attend la validation du Warsmith pour lancer les frégates."
    ),
    "PORTE_2_SPECIMEN": Porte(
        "2", "Le Specimen",
        "Le Warsmith valide le squelette viral extrait par BREACHER (Mode Vidéo)\n"
        "ou le rapport de territoire de GRAND_COMPASS (Mode Chaîne).\n"
        "Si rejet : l'Orchestrateur relance la frégate avec les notes du Warsmith."
    ),
    "PORTE_3_BLUEPRINT": Porte(
        "3", "Le Blueprint",
        "Le Warsmith valide le script généré par FORGEWARD.\n"
        "Si rejet : l'Orchestrateur relance FORGEWARD avec les notes du Warsmith."
    ),
    "PORTE_4_ARTEFACT": Porte(
        "4", "L'Artefact",
        "Le Warsmith valide l'artefact final (script + miniature OU rapport de niche).\n"
        "Si validé : l'artefact est sauvegardé dans ARCHIVUM/templates/. Le siège est terminé.\n"
        "Si archivé : l'artefact est conservé pour plus tard."
    ),
}

ORDRE_PORTES = ["PORTE_1_BRIEF", "PORTE_2_SPECIMEN", "PORTE_3_BLUEPRINT", "PORTE_4_ARTEFACT"]


def ouvrir_porte(gate_id: str):
    """Ouvre une porte spécifique."""
    key = f"PORTE_{gate_id}_{'BRIEF' if gate_id == '1' else 'SPECIMEN' if gate_id == '2' else 'BLUEPRINT' if gate_id == '3' else 'ARTEFACT'}"
    if key not in PORTES:
        raise ValueError(f"Porte inconnue: {gate_id}")
    PORTES[key].ouvrir()


def valider_porte(gate_id: str, notes: str = None):
    """Le Warsmith valide une porte."""
    key = f"PORTE_{gate_id}_{'BRIEF' if gate_id == '1' else 'SPECIMEN' if gate_id == '2' else 'BLUEPRINT' if gate_id == '3' else 'ARTEFACT'}"
    if key not in PORTES:
        raise ValueError(f"Porte inconnue: {gate_id}")
    PORTES[key].valider(notes)


def rejeter_porte(gate_id: str, notes: str = None):
    """Le Warsmith rejette une porte."""
    key = f"PORTE_{gate_id}_{'BRIEF' if gate_id == '1' else 'SPECIMEN' if gate_id == '2' else 'BLUEPRINT' if gate_id == '3' else 'ARTEFACT'}"
    if key not in PORTES:
        raise ValueError(f"Porte inconnue: {gate_id}")
    PORTES[key].rejeter(notes)


def porte_suivante(gate_actuelle: str) -> str | None:
    """Retourne la porte suivante, ou None si on est à la dernière."""
    if gate_actuelle is None:
        return ORDRE_PORTES[0]
    idx = ORDRE_PORTES.index(gate_actuelle) if gate_actuelle in ORDRE_PORTES else -1
    if idx + 1 < len(ORDRE_PORTES):
        return ORDRE_PORTES[idx + 1]
    return None


def portes_to_dict() -> dict:
    """Sérialise l'état des portes pour le ledger."""
    return {gid: porte.to_dict() for gid, porte in PORTES.items()}


def reset_portes():
    """Réinitialise toutes les portes (nouveau siège)."""
    for porte in PORTES.values():
        porte.statut = "VERROUILLEE"
        porte.inputs = {}
        porte.decision = None
        porte.notes = None
        porte.timestamp = None
