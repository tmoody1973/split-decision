"""Run one full deliberation and write episodes/{case_id}/events.jsonl (MOO-222).

Usage: python scripts/deliberate.py --case data/cases/cl-cluster-12345.json
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.chamber import Chamber  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True, help="path to a case record JSON")
    args = parser.parse_args()

    case = json.loads(Path(args.case).read_text(encoding="utf-8"))
    chamber = Chamber(case)
    log = chamber.run()

    out = REPO_ROOT / "episodes" / case["case_id"] / "events.jsonl"
    log.write(out)

    flips = log.of_type("vote_change")
    verdict = log.of_type("verdict")[0]
    print(f"\nevents: {len(log.events)} -> {out}")
    print(f"verdict: {verdict['position']} {verdict['vote_split']} "
          f"(dissenting: {', '.join(verdict['dissenters']) or 'none'})")
    print(f"vote changes: {len(flips)}")
    for f in flips:
        print(f"  - r{f['round']} {f['agent']}: {f['from']} -> {f['to']} "
              f"(influenced by {', '.join(f['influenced_by'])})\n    reason: {f['reason_text']}")
    reveals = log.of_type("reveal")
    if reveals:
        r = reveals[0]
        print(f"reveal: actual {r['actual']} {r['actual_split']} -> {'MATCH' if r['match'] else 'MISS'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
