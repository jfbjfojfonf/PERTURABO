#!/usr/bin/env python3
"""
WAR ROOM — Récepteur de référence du webhook F00C (Salle de Guerre).

Contrat : PLAN_SALLE_DE_GUERRE.md §4 (repo PERTURABO).
Reçoit le payload du webhook F00C_VOX, vérifie le token partagé, le stocke
dans docs/data/war_room.json et sert le dashboard (docs/war_room.html).

Endpoints :
    POST /                → payload F00C (X-Siege-Token requis si configuré)
    GET  /api/war-room    → JSON complet (dashboard, polling LIVE)
    POST /api/gate        → verdict Warsmith {run_id, candidate_id, verdict}
    GET  /                → docs/war_room.html ; /index.html ; fichiers docs/

Usage local :
    SIEGE_WEBHOOK_TOKEN=mon-secret python3 war_room/receiver.py
Test sans serveur :
    python3 war_room/receiver.py --self-test
"""
from __future__ import annotations

import argparse
import subprocess
import threading
import traceback
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:  # transcripts bilingues (yt-dlp) — optionnel : le dashboard doit rester debout sans
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import transcripts as transcripts_mod
except Exception:  # noqa: BLE001 - dégradation propre si le module manque
    transcripts_mod = None

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
DATA_PATH = DOCS_DIR / "data" / "war_room.json"
# Manifestes caviar émis par F00D (frégate compositeur) — indexés par candidat
CAVIAR_DIR = REPO_ROOT / "PERTURABO" / "MONDES_FORGES" / "CLIPPING" / \
    "F00_IRON_SENTINEL" / "F00D_NARRATIVUM" / "OUT"
CAVIAR_INDEX = REPO_ROOT / "docs" / "data" / "caviar_index.json"
REQUIRED_KEYS = ("run_id", "siege_id", "mode", "status", "source",
                 "heatmap", "replayed_curve", "fused_heatmap", "candidates", "pushed_at")
GATE_VERDICTS = ("approved", "rejected")
GATE_STYLES = ("split", "reframing", "ranking", "blur")
DEFAULT_STYLE = "reframing"
# Directeur Caviar (F00D) — import tolérant : la Salle de Guerre doit rester
# debout même si la frégate n'est pas déployée dans le workspace.
CAVIAR_DIRECTOR_PATH = REPO_ROOT / "PERTURABO" / "MONDES_FORGES" / "CLIPPING" \
    / "F00_IRON_SENTINEL" / "F00D_NARRATIVUM" / "CODEBASE" / "caviar_director.py"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_caviar_index(current_run_id: str = "") -> dict:
    """Manifestes caviar disponibles (candidate_id → manifeste ou refus).

    Le mapping candidat → fichier est écrit dans docs/data/caviar_index.json
    (par l'opérateur ou l'outil d'émission) ; cette fonction résout et charge.
    Garde-fou anti-mélange de runs : un manifeste émis pour un autre run que
    le run courant n'est PAS servi (les mêmes ids de candidats réapparaissent
    d'un run à l'autre — servir l'ancien serait mentir au cockpit).
    """
    if not CAVIAR_INDEX.exists():
        return {}
    try:
        index = json.loads(CAVIAR_INDEX.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    out = {}
    for candidate_id, rel in (index.get("manifests") or {}).items():
        p = Path(rel)
        if not p.is_absolute():
            p = REPO_ROOT / rel
        try:
            man = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            out[candidate_id] = {"refused": True, "reason": f"manifeste illisible: {rel}"}
            continue
        man_run = str((man.get("source") or {}).get("run_id") or "")
        if current_run_id and man_run and man_run != current_run_id:
            continue  # manifeste d'un run précédent : hors sujet pour ce run
        out[candidate_id] = man
    return out


def _load_doc() -> dict:
    if DATA_PATH.exists():
        try:
            return json.loads(DATA_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def validate_payload(payload: dict) -> tuple[bool, str]:
    """Valide le contrat : clés requises, mode/status connus, listes."""
    missing = [key for key in REQUIRED_KEYS if key not in payload]
    if missing:
        return False, f"clés manquantes : {', '.join(missing)}"
    if payload["mode"] not in ("vod", "live"):
        return False, f"mode inconnu : {payload['mode']!r} (attendu vod|live)"
    if payload["status"] not in ("full", "metadata_only", "metadata_only_media_error"):
        return False, f"status inconnu : {payload['status']!r}"
    if not isinstance(payload["candidates"], list):
        return False, "candidates doit être une liste"
    for curve, name in ((payload["heatmap"], "heatmap"), (payload["replayed_curve"], "replayed_curve"),
                        (payload["fused_heatmap"], "fused_heatmap")):
        if not isinstance(curve, list):
            return False, f"{name} doit être une liste"
    return True, "ok"


def store_payload(payload: dict) -> dict:
    """Persiste le dernier payload (VOD) et l'historique idempotent des runs.

    Mode LIVE : chaque run pousse un (ou peu de) candidat(s) — l'historique
    `runs` devient la file d'arrivée temps réel du dashboard.
    """
    doc = _load_doc()
    doc["last_pushed_at"] = _now_iso()
    doc["last_run"] = payload
    history = doc.setdefault("runs", {})
    history[payload["run_id"]] = {
        "siege_id": payload["siege_id"],
        "mode": payload["mode"],
        "status": payload["status"],
        "n_candidates": len(payload.get("candidates") or []),
        "received_at": doc["last_pushed_at"],
    }
    doc["total_runs"] = len(history)
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    _warm_transcripts_async(payload)
    return doc


def _warm_transcripts_async(payload: dict) -> None:
    """Préchauffe les transcripts FR/EN de tous les candidats en arrière-plan.

    Objectif : quand l'opérateur clique une carte, le transcript est déjà en
    cache — le clic reste instantané même si yt-dlp met 30 s (ou rate-limit).
    """
    if transcripts_mod is None:
        return
    source = (payload.get("source") or {}).get("reference") or ""
    run_id = payload.get("run_id") or ""
    cands = [c for c in (payload.get("candidates") or [])
             if c.get("id") and c.get("start_sec") is not None]
    if not source or not run_id or not cands:
        return

    def _warm():
        for cand in cands:
            try:
                transcripts_mod.build_candidate_transcript(source, run_id, cand)
            except Exception:  # noqa: BLE001 - le préchauffage ne casse jamais le récepteur
                pass
    threading.Thread(target=_warm, daemon=True, name="warm-transcripts").start()


def store_gate(run_id: str, candidate_id: str, verdict: str,
               style: str | None = None) -> tuple[dict, str]:
    """Enregistre un verdict Warsmith (gate GO/NO-GO + style) — le cockpit commande.

    Le style (split|reframing|ranking|blur) est choisi sur la carte AVANT le
    GO : il part avec le verdict et pilote la composition F00D du manifeste.
    Le pipeline (PERTURABO) lit GET /api/war-room pour récupérer les verdicts :
    c'est la boucle de retour Livraison D.
    """
    doc = _load_doc()
    run = doc.get("runs", {}).get(run_id)
    if run is None:
        return doc, f"run_id inconnu : {run_id!r}"
    if verdict not in GATE_VERDICTS:
        return doc, f"verdict inconnu : {verdict!r} (attendu approved|rejected)"
    if style is not None and style not in GATE_STYLES:
        return doc, f"style inconnu : {style!r} (attendu split|reframing|ranking|blur)"
    last_run = doc.get("last_run") or {}
    known = {c.get("id") for c in last_run.get("candidates") or []}
    if last_run.get("run_id") == run_id and candidate_id not in known:
        return doc, f"candidate_id inconnu dans {run_id}: {candidate_id!r}"
    gates = doc.setdefault("gates", {}).setdefault(run_id, {})
    previous_entry = gates.get(candidate_id) or {}
    if previous_entry.get("verdict") == verdict \
            and (style is None or previous_entry.get("style") == style):
        return doc, "ok"  # re-vote identique : idempotent, pas de double comptage
    previous = doc.get("last_verdicts", {}).get(f"{run_id}/{candidate_id}")
    if previous in GATE_VERDICTS and previous != verdict:
        counts = doc.setdefault("gate_counts", {"approved": 0, "rejected": 0, "pending": 0})
        counts[previous] = max(0, counts.get(previous, 0) - 1)
    counts = doc.setdefault("gate_counts", {"approved": 0, "rejected": 0, "pending": 0})
    entry = {"verdict": verdict, "decided_at": _now_iso()}
    if style is not None:
        entry["style"] = style
    elif previous_entry.get("style"):
        entry["style"] = previous_entry["style"]  # GO sans style → style conservé
    gates[candidate_id] = entry
    doc.setdefault("last_verdicts", {})[f"{run_id}/{candidate_id}"] = verdict
    counts[verdict] = counts.get(verdict, 0) + 1
    DATA_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc, "ok"


# ─────────────────────────────────────────────────────────────────────────────
# F00D — émission caviar pilotée par le gate (style choisi au cockpit)
# ─────────────────────────────────────────────────────────────────────────────

def _load_director():
    """Charge caviar_director.py (F00D) — None si absent (dégradation propre)."""
    if not CAVIAR_DIRECTOR_PATH.exists():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location("caviar_director", CAVIAR_DIRECTOR_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def emit_caviar_for_gate(run_id: str, candidate_id: str, style: str) -> dict:
    """GO enregistré → F00D compose le manifeste avec le style du cockpit.

    Retourne {"status": "emitted"|"refused"|"unavailable"|"error", ...}.
    L'échec d'émission ne remet JAMAIS en cause le verdict (déjà acté) : le
    diagnostic est journalisé dans le doc et visible via caviar_index.
    """
    doc = _load_doc()
    last = doc.get("last_run") or {}
    cand = next((c for c in last.get("candidates") or [] if c.get("id") == candidate_id), None)
    if cand is None or last.get("run_id") != run_id:
        return {"status": "error", "reason": f"candidat {candidate_id!r} hors run courant"}
    director = _load_director()
    if director is None:
        return {"status": "unavailable", "reason": "caviar_director.py introuvable (F00D absent)"}

    budget = director.load_budget()
    duration = float(cand.get("duration_sec") or (cand.get("end_sec", 0) - cand.get("start_sec", 0)) or 30.0)
    fused = last.get("fused_heatmap") or []
    in_seg = [b for b in fused
              if b.get("start_sec") is not None
              and b.get("start_sec") >= (cand.get("start_sec") or 0)
              and b.get("end_sec") is not None
              and b.get("end_sec") <= (cand.get("end_sec") or 1e18)]
    segment_heatmap = [{
        "start_sec": round(b["start_sec"] - (cand.get("start_sec") or 0), 3),
        "end_sec": round(b["end_sec"] - (cand.get("start_sec") or 0), 3),
        "attention_norm": b.get("attention_norm", b.get("fused_norm", 0.5)),
    } for b in in_seg] or [{"start_sec": 0.0, "end_sec": duration,
                            "attention_norm": min(cand.get("signal_intensity") or 0.6, 1.0)}]

    input_doc = {
        "schema_version": "caviar_input.v1",
        "candidate": {
            "run_id": run_id,
            "candidate_id": candidate_id,
            "source": (last.get("source") or {}).get("reference") or "",
            "title": last.get("title") or "",
            "start_sec_source": cand.get("start_sec"),
            "end_sec_source": cand.get("end_sec"),
            "duration_sec": round(duration, 3),
            "score": cand.get("score"),
            "gate": "approved",
            "gate_decided_by": "warsmith (cockpit War Room)",
            "style_hint": style,
        },
        "segment_heatmap": segment_heatmap,
        "constraints": {"style": style},
    }

    out_dir = CAVIAR_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"caviar_manifest_{candidate_id}.json"
    try:
        with tempfile.TemporaryDirectory() as td:
            in_path = Path(td) / "caviar_input.json"
            in_path.write_text(json.dumps(input_doc, ensure_ascii=False, indent=2), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(CAVIAR_DIRECTOR_PATH),
                 "--input", str(in_path), "--out", str(out_path)],
                capture_output=True, text=True, timeout=120, check=False)
    except (subprocess.SubprocessError, OSError) as exc:
        return {"status": "error", "reason": f"F00D injoignable : {exc}"}

    emitted = out_path.exists()
    try:
        out_rel = str(out_path.relative_to(REPO_ROOT))
    except ValueError:  # out_path hors du repo (tests, sandbox) : chemin absolu
        out_rel = str(out_path)
    note = {"status": "emitted" if (emitted and proc.returncode == 0) else "refused",
            "style": style, "out": out_rel if emitted else None,
            "reason": (proc.stderr or proc.stdout or "").strip()[-400:] or None}
    idx = {}
    if CAVIAR_INDEX.exists():
        try:
            idx = json.loads(CAVIAR_INDEX.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            idx = {}
    manifests = idx.setdefault("manifests", {})
    if note["status"] == "emitted":
        manifests[candidate_id] = out_rel
        idx["note"] = ("Mapping candidate_id → chemin du caviar_manifest.json émis par F00D "
                       "(style choisi au cockpit). Chemins relatifs à la racine du repo connecté.")
        try:
            CAVIAR_INDEX.parent.mkdir(parents=True, exist_ok=True)
            CAVIAR_INDEX.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass
    return note


def clear_gate(run_id: str, candidate_id: str) -> tuple[dict, str]:
    """Révoque un verdict (bouton « retirer ») : la carte redevient en attente."""
    doc = _load_doc()
    gates = doc.get("gates", {}).get(run_id, {})
    entry = gates.get(candidate_id)
    if not entry:
        return doc, f"pas de verdict à retirer pour {candidate_id!r} dans {run_id!r}"
    verdict = entry.get("verdict")
    doc["gates"][run_id].pop(candidate_id, None)
    doc.get("last_verdicts", {}).pop(f"{run_id}/{candidate_id}", None)
    counts = doc.setdefault("gate_counts", {"approved": 0, "rejected": 0, "pending": 0})
    if verdict in counts:
        counts[verdict] = max(0, counts[verdict] - 1)
    DATA_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc, "ok"


def reset_all(full: bool = False) -> dict:
    """Bouton RESET : verdicts + compteurs à zéro. full=True vide aussi les runs.

    Les manifestes caviar déjà émis sont conservés (traçables dans l'Archivum
    F00D) ; le cockpit repart à zéro, l'historique reste chez la frégate.
    """
    doc = _load_doc()
    keep = {"last_pushed_at": doc.get("last_pushed_at")}
    if not full:
        keep.update({k: doc.get(k) for k in ("last_run", "runs", "total_runs") if k in doc})
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(keep, ensure_ascii=False, indent=2), encoding="utf-8")
    return keep


def make_handler(token: str):
    class SiegeHandler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - API http.server
            try:
                self._do_POST_safe()
            except (BrokenPipeError, ConnectionResetError):
                pass  # client parti avant la réponse : rien à faire
            except Exception as exc:  # noqa: BLE001 - une erreur ne tue jamais le serveur
                traceback.print_exc()
                try:
                    self._reply(500, {"error": f"erreur interne récepteur : {exc}"})
                except Exception:  # noqa: BLE001
                    pass

        def _do_POST_safe(self):  # noqa: N802 - API http.server
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            # Le token partagé protège le webhook F00C (POST /). La gate du
            # cockpit (/api/gate) est validée par run_id + candidate_id ; pour
            # la production, placer le dashboard derrière une auth reverse-proxy.
            if token and not self.path.startswith("/api/gate") \
                    and self.headers.get("X-Siege-Token") != token:
                self._reply(401, {"error": "token invalide ou absent (X-Siege-Token)"})
                return
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as exc:
                self._reply(400, {"error": f"JSON invalide : {exc}"})
                return
            if self.path.startswith("/api/reset"):
                full = "full=1" in (self.path or "") or bool(payload.get("full"))
                doc = reset_all(full=full)
                self._reply(200, {"accepted": True, "reset": "full" if full else "gates",
                                  "gate_counts": {"approved": 0, "rejected": 0, "pending": 0}})
                return
            if self.path.startswith("/api/gate"):
                run_id = payload.get("run_id") or ""
                candidate_id = payload.get("candidate_id") or ""
                verdict = payload.get("verdict") or ""
                if verdict == "clear":
                    doc, reason = clear_gate(run_id, candidate_id)
                    if reason != "ok":
                        self._reply(422, {"error": reason})
                        return
                    self._reply(200, {"accepted": True, "run_id": run_id,
                                      "candidate_id": candidate_id, "verdict": "clear",
                                      "gate_counts": doc.get("gate_counts")})
                    return
                style = payload.get("style") or None
                doc, reason = store_gate(run_id, candidate_id, verdict, style)
                if reason != "ok":
                    self._reply(422, {"error": reason})
                    return
                caviar = None
                if verdict == "approved":
                    chosen = style \
                        or ((doc.get("gates") or {}).get(run_id, {}).get(candidate_id, {}) or {}).get("style") \
                        or DEFAULT_STYLE
                    caviar = emit_caviar_for_gate(run_id, candidate_id, chosen)
                self._reply(200, {"accepted": True, "run_id": run_id,
                                  "candidate_id": candidate_id, "verdict": verdict,
                                  "style": style,
                                  "caviar": caviar,
                                  "gate_counts": doc.get("gate_counts")})
                return
            ok, reason = validate_payload(payload)
            if not ok:
                self._reply(422, {"error": f"payload invalide : {reason}"})
                return
            doc = store_payload(payload)
            gates = (doc.get("gates") or {}).get(payload["run_id"]) or {}
            self._reply(200, {"accepted": True, "run_id": payload["run_id"],
                              "total_runs": doc["total_runs"], "existing_gates": gates})

        def do_GET(self):  # noqa: N802
            try:
                self._do_GET_safe()
            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as exc:  # noqa: BLE001 - une erreur ne tue jamais le serveur
                traceback.print_exc()
                try:
                    self._reply(500, {"error": f"erreur interne récepteur : {exc}"})
                except Exception:  # noqa: BLE001
                    pass

        def _do_GET_safe(self):  # noqa: N802
            path = self.path.split("?")[0]
            if path.startswith("/api/transcript"):
                self._handle_transcript(self.path)  # self.path = query incluse
                return
            if path.startswith("/api/war-room"):
                doc = _load_doc()
                last_run_id = ((doc.get("last_run") or {}).get("run_id")) or ""
                doc["caviar_manifests"] = _load_caviar_index(last_run_id)
                # compteur pending recalculé (vérité depuis les données)
                last = doc.get("last_run") or {}
                gates = (doc.get("gates") or {}).get(last.get("run_id", ""), {})
                pending = sum(1 for c in last.get("candidates", [])
                              if c.get("id") not in gates)
                doc.setdefault("gate_counts", {})["pending"] = pending
                self._reply(200, doc)
                return
            if path in ("/", "/war-room", "/war_room.html"):
                self._serve_file(DOCS_DIR / "war_room.html")
                return
            if path == "/index.html" or path == "/radar":
                self._serve_file(DOCS_DIR / "index.html")
                return
            safe = (DOCS_DIR / path.lstrip("/")).resolve()
            if safe.is_file() and str(safe).startswith(str(DOCS_DIR.resolve())):
                self._serve_file(safe)
                return
            self._reply(404, {"error": "route inconnue (POST /, /api/gate ; GET /api/war-room, /)"})

        def _handle_transcript(self, path: str) -> None:
            """GET /api/transcript?candidate=voxc-2[&run_id=…] → {fr, en, …}"""
            if transcripts_mod is None:
                self._reply(200, {"available": False,
                                  "note": "module transcripts indisponible côté serveur"})
                return
            from urllib.parse import parse_qs, urlparse
            qs = parse_qs(urlparse(path).query)
            run_id = (qs.get("run_id") or [""])[0]
            candidate_id = (qs.get("candidate") or [""])[0]
            doc = _load_doc()
            last = doc.get("last_run") or {}
            if run_id and run_id != last.get("run_id"):
                # run précis demandé mais pas le dernier : on cherche dans l'historique léger
                self._reply(200, {"available": False,
                                  "note": f"run {run_id!r} non servi en transcript (dernier run : {last.get('run_id')!r})"})
                return
            cand = next((c for c in last.get("candidates") or []
                         if c.get("id") == candidate_id), None)
            if cand is None:
                self._reply(422, {"error": f"candidat inconnu : {candidate_id!r}"})
                return
            source = (last.get("source") or {}).get("reference") or ""
            if not source:
                self._reply(200, {"available": False, "note": "source inconnue"})
                return
            try:
                out = transcripts_mod.build_candidate_transcript(
                    source, last["run_id"], cand)
            except Exception as exc:  # noqa: BLE001 - repli propre (429, réseau…)
                out = {"available": False,
                       "note": f"transcript indisponible : {exc}"}
            self._reply(200, out)

        def _serve_file(self, file_path: Path) -> None:
            types = {".html": "text/html", ".json": "application/json",
                     ".js": "text/javascript", ".css": "text/css",
                     ".png": "image/png", ".svg": "image/svg+xml"}
            try:
                body = file_path.read_bytes()
            except OSError:
                self._reply(404, {"error": "fichier introuvable"})
                return
            self.send_response(200)
            self.send_header("Content-Type",
                             types.get(file_path.suffix, "application/octet-stream"))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):  # noqa: A003 - logs propres
            sys.stderr.write("[war-room] " + (fmt % args) + "\n")

        def _reply(self, status: int, body: dict) -> None:
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    return SiegeHandler


def self_test() -> int:
    """Round-trip complet : payload → validation → stockage → gate.

    Non destructif : l'état réel (docs/data/war_room.json) est restauré après.
    """
    real_doc = _load_doc()  # sauvegarde — le test ne doit jamais écraser le réel
    sample = {
        "run_id": "f00c_selftest",
        "siege_id": "SOPHIE_RAIN_TEST",
        "mode": "vod",
        "status": "full",
        "source": {"reference": "https://www.youtube.com/watch?v=qm3E3cchBmQ",
                   "platform": "youtube", "content_type": "video"},
        "heatmap": [{"bucket": 0, "start_sec": 0.0, "end_sec": 1.0,
                     "attention": 0.5, "attention_norm": 1.0}],
        "replayed_curve": [{"start": 0.0, "end": 1.0, "value": 0.8}],
        "fused_heatmap": [],
        "candidates": [{"id": "clip_01", "rank": 1, "start_sec": 0.0, "end_sec": 1.0,
                        "score": 0.8, "platforms": ["youtube_shorts"]}],
        "pushed_at": _now_iso(),
    }
    ok, reason = validate_payload(sample)
    assert ok, f"payload d'exemple invalide : {reason}"
    doc = store_payload(sample)
    assert doc["total_runs"] >= 1
    ok, _ = validate_payload({"run_id": "x"})
    assert not ok, "un payload incomplet doit être rejeté"
    doc, reason = store_gate("f00c_selftest", "clip_01", "approved")
    assert reason == "ok", reason
    assert doc["gates"]["f00c_selftest"]["clip_01"]["verdict"] == "approved"
    doc, reason = store_gate("f00c_selftest", "clip_01", "maybe")
    assert reason != "ok", "un verdict inconnu doit être rejeté"
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(real_doc, ensure_ascii=False, indent=2), encoding="utf-8")  # restauration
    print(f"SELF-TEST OK — {DATA_PATH} (runs: {doc['total_runs']}, état réel restauré)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WAR ROOM — récepteur webhook F00C + dashboard")
    parser.add_argument("--port", type=int, default=None,
                        help="Port d'écoute (défaut : env PORT, sinon 8787)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    port = args.port or int(os.environ.get("PORT") or 8787)
    token = os.environ.get("SIEGE_WEBHOOK_TOKEN", "")
    if not token:
        print("WAR ROOM: WARNING — SIEGE_WEBHOOK_TOKEN vide : POSTs non authentifiés acceptés.",
              file=sys.stderr)
    server = ThreadingHTTPServer(("0.0.0.0", port), make_handler(token))
    print(f"WAR ROOM prêt sur 0.0.0.0:{port} — dashboard /, POST / (X-Siege-Token), "
          "POST /api/gate, GET /api/transcript, GET /api/war-room")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
