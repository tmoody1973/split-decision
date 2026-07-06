"""Live Bench — judge-facing realtime deliberation demo (MOO-226 ext).

A deliberately tiny stdlib HTTP service that lets a hackathon judge convene
the agent society ON THIS INSTANCE and watch the event log stream as the
jurists argue. No framework deps; runs from the repo venv for engine imports.

Endpoints (proxied by nginx under /api/):
  POST /api/convene        -> start a run (409 if one is live, 429 in cooldown)
  GET  /api/status         -> {"state": idle|running|cooldown, "run_id", ...}
  GET  /api/log?from=N     -> events[N:] of the active/most recent run

Guardrails: one run at a time; cooldown between runs; daily cap. The demo
case is fixed (decided case, so nothing here can contradict the published
pending-case predictions).
"""

import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path("/opt/split-decision")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from qwen_client import load_dotenv  # noqa: E402

load_dotenv()

from engine.chamber import Chamber  # noqa: E402

PORT = 8787
# Pung v. Isabella County — the podcast case: proven clean through the full
# pipeline (moderation-safe), decided 9-0, so judges can grade the live panel.
DEMO_CASE = REPO_ROOT / "data" / "cases" / "cl-cluster-10878534.json"
STATE_DIR = Path("/var/lib/split-decision-livebench")
COOLDOWN_S = 20 * 60
DAILY_CAP = 12

_lock = threading.Lock()
_state = {"state": "idle", "run_id": None, "started": None, "finished": None,
          "case_name": None, "error": None, "runs_today": 0, "day": None}
_events: list[dict] = []


def _now() -> float:
    return time.time()


def _day() -> str:
    return time.strftime("%Y-%m-%d")


def _public_state() -> dict:
    s = dict(_state)
    if s["state"] == "cooldown" and s["finished"]:
        s["cooldown_remaining_s"] = max(0, int(COOLDOWN_S - (_now() - s["finished"])))
    s["event_count"] = len(_events)
    s.pop("runs_today", None)
    return s


def _tick() -> None:
    """Advance cooldown -> idle lazily."""
    if _state["state"] == "cooldown" and _state["finished"] and \
            _now() - _state["finished"] > COOLDOWN_S:
        _state["state"] = "idle"


def _run_deliberation(run_id: str) -> None:
    global _events
    try:
        case = json.loads(DEMO_CASE.read_text(encoding="utf-8"))
        case["case_id"] = run_id  # isolate output from real episodes
        chamber = Chamber(case)
        orig_add = chamber.log.add

        def streaming_add(**payload):
            event = orig_add(**payload)
            with _lock:
                _events.append(event)
            return event

        chamber.log.add = streaming_add
        log = chamber.run()
        out_dir = STATE_DIR / "runs" / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        log.write(out_dir / "events.jsonl")
        with _lock:
            _state["error"] = None
    except Exception as exc:  # noqa: BLE001 — surface anything to the page
        with _lock:
            _state["error"] = f"{type(exc).__name__}: {exc}"[:300]
    finally:
        with _lock:
            _state["state"] = "cooldown"
            _state["finished"] = _now()


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):  # quiet
        pass

    def do_GET(self):  # noqa: N802
        with _lock:
            _tick()
            if self.path.startswith("/api/status"):
                return self._json(200, _public_state())
            if self.path.startswith("/api/log"):
                try:
                    frm = int(self.path.split("from=")[1].split("&")[0]) if "from=" in self.path else 0
                except ValueError:
                    frm = 0
                return self._json(200, {"from": frm, "events": _events[frm:],
                                        "total": len(_events), "state": _public_state()})
        return self._json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        global _events
        if not self.path.startswith("/api/convene"):
            return self._json(404, {"error": "not found"})
        with _lock:
            _tick()
            if _state["day"] != _day():
                _state["day"], _state["runs_today"] = _day(), 0
            if _state["state"] == "running":
                return self._json(409, {"error": "the panel is already in session — watch along",
                                        **_public_state()})
            if _state["state"] == "cooldown":
                return self._json(429, {"error": "the panel is in recess", **_public_state()})
            if _state["runs_today"] >= DAILY_CAP:
                return self._json(429, {"error": "daily session cap reached", **_public_state()})
            run_id = f"live-{time.strftime('%Y%m%d-%H%M%S')}"
            case_name = json.loads(DEMO_CASE.read_text(encoding="utf-8"))["name"]
            _events = []
            _state.update(state="running", run_id=run_id, started=_now(),
                          finished=None, case_name=case_name, error=None)
            _state["runs_today"] += 1
        threading.Thread(target=_run_deliberation, args=(run_id,), daemon=True).start()
        return self._json(200, _public_state())


def main() -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"livebench on 127.0.0.1:{PORT}, demo case: {DEMO_CASE.name}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
