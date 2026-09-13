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
import traceback
import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO_ROOT / "docs"
DATA_PATH = DOCS_DIR / "data" / "war_room.json"
REQUIRED_KEYS = ("run_id", "siege_id", "mode", "status", "source",
                 "heatmap", "replayed_curve", "fused_heatmap", "candidates", "pushed_at")
GATE_VERDICTS = ("approved", "rejected")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    return doc


def store_gate(run_id: str, candidate_id: str, verdict: str) -> tuple[dict, str]:
    """Enregistre un verdict Warsmith (gate GO/NO-GO) — le cockpit commande.

    Le pipeline (PERTURABO) lit GET /api/war-room pour récupérer les verdicts :
    c'est la boucle de retour Livraison D.
    """
    doc = _load_doc()
    run = doc.get("runs", {}).get(run_id)
    if run is None:
        return doc, f"run_id inconnu : {run_id!r}"
    if verdict not in GATE_VERDICTS:
        return doc, f"verdict inconnu : {verdict!r} (attendu approved|rejected)"
    last_run = doc.get("last_run") or {}
    known = {c.get("id") for c in last_run.get("candidates") or []}
    if last_run.get("run_id") == run_id and candidate_id not in known:
        return doc, f"candidate_id inconnu dans {run_id}: {candidate_id!r}"
    gates = doc.setdefault("gates", {}).setdefault(run_id, {})
    if gates.get(candidate_id, {}).get("verdict") == verdict:
        return doc, "ok"  # re-vote identique : idempotent, pas de double comptage
    gates[candidate_id] = {"verdict": verdict, "decided_at": _now_iso()}
    counts = doc.setdefault("gate_counts", {"approved": 0, "rejected": 0, "pending": 0})
    previous = doc.get("last_verdicts", {}).get(f"{run_id}/{candidate_id}")
    if previous in GATE_VERDICTS and previous != verdict:
        counts[previous] = max(0, counts.get(previous, 0) - 1)
    doc.setdefault("last_verdicts", {})[f"{run_id}/{candidate_id}"] = verdict
    counts[verdict] = counts.get(verdict, 0) + 1
    DATA_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc, "ok"


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
            if self.path.startswith("/api/gate"):
                run_id = payload.get("run_id") or ""
                candidate_id = payload.get("candidate_id") or ""
                verdict = payload.get("verdict") or ""
                doc, reason = store_gate(run_id, candidate_id, verdict)
                if reason != "ok":
                    self._reply(422, {"error": reason})
                    return
                self._reply(200, {"accepted": True, "run_id": run_id,
                                  "candidate_id": candidate_id, "verdict": verdict,
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
            if path.startswith("/api/war-room"):
                doc = _load_doc()
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
          "POST /api/gate, GET /api/war-room")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
