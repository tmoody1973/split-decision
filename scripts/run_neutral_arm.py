"""Neutral-panel control arm (MOO-253): condition C with nine neutral analysts.

Disentangles "deliberation made agents worse" from "committed archetypes made
agents worse": the identical protocol runs on the identical 24-case sample with
personas/neutral (no interpretive ideology; flip trigger = a genuinely better
argument). Episodes land in episodes/neutral-<case_id>/ — the originals are
never touched. Resumable: completed neutral episodes are skipped.

Usage (overnight batch):
  nohup caffeinate -i .venv/bin/python scripts/run_neutral_arm.py > neutral_arm.log 2>&1 &
"""

import json
import os
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Must be set BEFORE the chamber imports/loads the registry.
os.environ["SD_PERSONA_DIR"] = str(REPO_ROOT / "personas" / "neutral")

from engine.chamber import Chamber  # noqa: E402

MANIFEST = REPO_ROOT / "data" / "benchmark_manifest.json"
CASES_DIR = REPO_ROOT / "data" / "cases"
EPISODES = REPO_ROOT / "episodes"
CONCURRENT_CASES = 2  # each case already fans nine jurors in parallel


def run_case(case_id: str) -> str:
    neutral_id = f"neutral-{case_id}"
    out = EPISODES / neutral_id / "events.jsonl"
    if out.exists():
        return f"skip {neutral_id} (exists)"
    case = json.loads((CASES_DIR / f"{case_id}.json").read_text(encoding="utf-8"))
    case = {**case, "case_id": neutral_id}
    try:
        log = Chamber(case).run()
        log.write(out)
        verdict = log.of_type("verdict")[0]
        return (f"done {neutral_id}: {verdict['position']} {verdict['vote_split']}, "
                f"{len(log.of_type('vote_change'))} flips")
    except Exception as err:  # noqa: BLE001 — one failed case must not kill the batch
        traceback.print_exc()
        return f"FAIL {neutral_id}: {type(err).__name__}: {str(err)[:200]}"


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    # The control mirrors the C sample exactly: cases with an existing episode.
    targets = [e["case_id"] for e in manifest["benchmark"]
               if (EPISODES / e["case_id"] / "events.jsonl").exists()]
    print(f"neutral arm: {len(targets)} cases, {CONCURRENT_CASES} concurrent", flush=True)
    with ThreadPoolExecutor(max_workers=CONCURRENT_CASES) as pool:
        for line in pool.map(run_case, targets):
            print(line, flush=True)
    print("neutral arm complete", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
