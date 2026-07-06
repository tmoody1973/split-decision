"""Live Bench child runner: one deliberation, streamed to disk (MOO-226 ext).

Runs detached from the server (start_new_session), so livebench_server
restarts — unattended-upgrades, deploys — never kill a judge's session.
Every event is appended to <run_dir>/stream.jsonl the moment the agent
produces it; <run_dir>/done.json marks completion or failure.

Usage: run_deliberation.py <case_json_path> <run_dir>
"""

import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path("/opt/split-decision")
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from qwen_client import load_dotenv  # noqa: E402

load_dotenv()

from engine.chamber import Chamber  # noqa: E402


def main() -> int:
    case_path, run_dir = Path(sys.argv[1]), Path(sys.argv[2])
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "pid").write_text(str(os.getpid()))
    stream = (run_dir / "stream.jsonl").open("a", buffering=1, encoding="utf-8")
    try:
        case = json.loads(case_path.read_text(encoding="utf-8"))
        case["case_id"] = run_dir.name  # isolate output from real episodes
        chamber = Chamber(case)
        orig_add = chamber.log.add

        def streaming_add(**payload):
            event = orig_add(**payload)
            stream.write(json.dumps(event) + "\n")
            return event

        chamber.log.add = streaming_add
        log = chamber.run()
        log.write(run_dir / "events.jsonl")
        (run_dir / "done.json").write_text(json.dumps(
            {"ok": True, "finished": time.time()}))
    except Exception as exc:  # noqa: BLE001 — judge-facing surface
        (run_dir / "done.json").write_text(json.dumps(
            {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300],
             "finished": time.time()}))
        return 1
    finally:
        stream.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
