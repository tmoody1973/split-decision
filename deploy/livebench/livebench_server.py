"""Live Bench — judge-facing realtime deliberation demo (MOO-226 ext).

A deliberately tiny stdlib HTTP service that lets a hackathon judge convene
the agent society ON THIS INSTANCE and watch the event log stream as the
jurists argue. No framework deps.

Design: the server is STATELESS. Each deliberation runs as a detached
subprocess (deploy/livebench/run_deliberation.py) writing stream.jsonl /
done.json / pid under /var/lib/split-decision-livebench/runs/<run_id>/ —
so server restarts (deploys, unattended-upgrades) never kill a session.

Endpoints (proxied by nginx under /api/):
  POST /api/convene        -> start a run (409 if one is live, 429 in cooldown)
  GET  /api/status         -> {"state": idle|running|cooldown, ...}
  GET  /api/log?from=N     -> events[N:] of the latest run

Guardrails: one run at a time; cooldown between runs; daily cap. The demo
case is fixed to Pung v. Isabella County — proven moderation-safe through the
full pipeline, decided (9-0), so live runs can never contradict the published
pending-case predictions.
"""

import json
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path("/opt/split-decision")
PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
RUNNER = REPO_ROOT / "deploy" / "livebench" / "run_deliberation.py"
DEMO_CASE = REPO_ROOT / "data" / "cases" / "cl-cluster-10878534.json"
RUNS_DIR = Path("/var/lib/split-decision-livebench/runs")

PORT = 8787
COOLDOWN_S = 20 * 60
DAILY_CAP = 12


def _latest_run() -> Path | None:
    runs = sorted(RUNS_DIR.glob("live-*"))
    return runs[-1] if runs else None


def _pid_alive(run: Path) -> bool:
    try:
        pid = int((run / "pid").read_text().strip())
        return Path(f"/proc/{pid}").exists()
    except (FileNotFoundError, ValueError):
        return False


def _done(run: Path) -> dict | None:
    try:
        return json.loads((run / "done.json").read_text())
    except FileNotFoundError:
        return None


def _meta(run: Path) -> dict:
    try:
        return json.loads((run / "meta.json").read_text())
    except FileNotFoundError:
        return {}


def _events(run: Path) -> list[dict]:
    try:
        with (run / "stream.jsonl").open(encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
    except FileNotFoundError:
        return []


def status() -> dict:
    run = _latest_run()
    if run is None:
        return {"state": "idle", "run_id": None, "case_name": None,
                "error": None, "event_count": 0}
    done = _done(run)
    if done is None and not _pid_alive(run):
        # runner died without reporting (e.g. hard reboot) — close it out
        done = {"ok": False, "error": "the session was interrupted; the panel will re-convene",
                "finished": time.time()}
        (run / "done.json").write_text(json.dumps(done))
    base = {"run_id": run.name, "case_name": _meta(run).get("case_name"),
            "event_count": len(_events(run)), "error": None}
    if done is None:
        return {"state": "running", **base}
    cooldown = COOLDOWN_S if done.get("ok") else 120  # brief recess after failures
    remaining = int(cooldown - (time.time() - done["finished"]))
    if not done.get("ok"):
        base["error"] = done.get("error")
    if remaining > 0:
        return {"state": "cooldown", "cooldown_remaining_s": remaining, **base}
    return {"state": "idle", **base}


def _runs_today() -> int:
    prefix = f"live-{time.strftime('%Y%m%d')}"
    return len(list(RUNS_DIR.glob(prefix + "*")))


def convene() -> tuple[int, dict]:
    s = status()
    if s["state"] == "running":
        return 409, {"error": "the panel is already in session — watch along", **s}
    if s["state"] == "cooldown":
        return 429, {"error": "the panel is in recess", **s}
    if _runs_today() >= DAILY_CAP:
        return 429, {"error": "daily session cap reached", **s}
    run_id = f"live-{time.strftime('%Y%m%d-%H%M%S')}"
    run = RUNS_DIR / run_id
    run.mkdir(parents=True, exist_ok=True)
    case_name = json.loads(DEMO_CASE.read_text(encoding="utf-8"))["name"]
    (run / "meta.json").write_text(json.dumps(
        {"case_name": case_name, "started": time.time()}))
    # systemd-run puts the runner in its OWN transient unit (own cgroup), so
    # restarting livebench never kills a judge's session. start_new_session
    # alone is NOT enough — children share the service cgroup and die with it
    # (verified live 2026-07-06). The runner writes its own pidfile.
    subprocess.run(
        ["systemd-run", "--collect", f"--unit=sd-{run_id}",
         f"--property=WorkingDirectory={REPO_ROOT}",
         str(PYTHON), str(RUNNER), str(DEMO_CASE), str(run)],
        check=True, capture_output=True)
    return 200, status()


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
        if self.path.startswith("/api/status"):
            return self._json(200, status())
        if self.path.startswith("/api/log"):
            try:
                frm = int(self.path.split("from=")[1].split("&")[0]) if "from=" in self.path else 0
            except ValueError:
                frm = 0
            run = _latest_run()
            events = _events(run) if run else []
            return self._json(200, {"from": frm, "events": events[frm:],
                                    "total": len(events), "state": status()})
        return self._json(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if not self.path.startswith("/api/convene"):
            return self._json(404, {"error": "not found"})
        code, payload = convene()
        return self._json(code, payload)


def main() -> int:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"livebench on 127.0.0.1:{PORT}, demo case: {DEMO_CASE.name} (stateless, disk-backed)")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
