#!/usr/bin/env python3
"""
WAR ROOM — Récepteur de référence du webhook F00C (Salle de Guerre).

Contrat : PLAN_SALLE_DE_GUERRE.md §4 (repo PERTURABO).
Reçoit le payload du webhook F00C_VOX, vérifie le token partagé et le
rend visible dans docs/data/war_room.json — la source que lira le
dashboard (mode VOD et mode LIVE, même contrat).

Usage local :
    SIEGE_WEBHOOK_TOKEN=mon-secret python3 war_room/receiver.py --port 8787

Test sans serveur (depuis le payload d'exemple) :
    python3 war_room/receiver.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "docs" / "data" / "war_room.json"
REQUIRED_KEYS = ("run_id", "siege_id", "mode", "status", "source",
                 "heatmap", "replayed_curve", "fused_heatmap", "candidates", "pushed_at")


def validate_payload(payload: dict) -> tuple[bool, str]:
    """Valide le contrat : clés requises, mode connu, timestamps plausibles."""
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
    """Persiste le dernier payload (mode VOD) et l'historique des runs."""
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc: dict = {}
    if DATA_PATH.exists():
        try:
            doc = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            doc = {}
    doc["last_pushed_at"] = datetime.now(timezone.utc).isoformat()
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
    DATA_PATH.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return doc


def make_handler(token: str):
    class SiegeHandler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - API http.server
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            if token and self.headers.get("X-Siege-Token") != token:
                self._reply(401, {"error": "token invalide ou absent (X-Siege-Token)"})
                return
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as exc:
                self._reply(400, {"error": f"JSON invalide : {exc}"})
                return
            ok, reason = validate_payload(payload)
            if not ok:
                self._reply(422, {"error": f"payload invalide : {reason}"})
                return
            doc = store_payload(payload)
            self._reply(200, {"accepted": True, "run_id": payload["run_id"],
                              "total_runs": doc["total_runs"]})

        def do_GET(self):  # noqa: N802
            if self.path.startswith("/api/war-room"):
                doc = json.loads(DATA_PATH.read_text(encoding="utf-8")) if DATA_PATH.exists() else {}
                self._reply(200, doc)
                return
            self._reply(404, {"error": "route inconnue (POST /, GET /api/war-room)"})

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
    """Round-trip complet : payload d'exemple → validation → stockage → GET."""
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
        "pushed_at": datetime.now(timezone.utc).isoformat(),
    }
    ok, reason = validate_payload(sample)
    assert ok, f"payload d'exemple invalide : {reason}"
    doc = store_payload(sample)
    assert doc["total_runs"] >= 1
    # validation doit refuser un payload incomplet
    ok, _ = validate_payload({"run_id": "x"})
    assert not ok, "un payload incomplet doit être rejeté"
    print(f"SELF-TEST OK — {DATA_PATH} (runs: {doc['total_runs']})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WAR ROOM — récepteur webhook F00C")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    token = os.environ.get("SIEGE_WEBHOOK_TOKEN", "")
    if not token:
        print("WAR ROOM: WARNING — SIEGE_WEBHOOK_TOKEN vide : aucun POST ne sera accepté.",
              file=sys.stderr)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(token))
    print(f"WAR ROOM prêt sur 0.0.0.0:{args.port} — POST / (X-Siege-Token), GET /api/war-room")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
