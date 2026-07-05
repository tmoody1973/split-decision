"""Produce one podcast episode from a deliberation event log.

Usage:
  .venv/bin/python scripts/run_episode.py --case cl-cluster-10878534
  ... --from tts        # resume from a pass (clips|script|tts|timestamps|assemble|publish)
  ... --until assemble  # stop after a pass (skip publish)

Each pass is idempotent: clip manifest / script are only regenerated when absent
(or when the run starts at that pass); TTS reuses existing mp3s.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from producer.assemble import assemble, assemble_deliberation  # noqa: E402
from producer.clips import select_clips  # noqa: E402
from producer.episode import load_episode  # noqa: E402
from producer.rss import publish_episode  # noqa: E402
from producer.script_pass import write_script  # noqa: E402
from producer.timeline import run_timestamp_pass  # noqa: E402
from producer.tts import tts_episode  # noqa: E402

PASSES = ["clips", "script", "tts", "timestamps", "assemble", "publish"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--from", dest="start", choices=PASSES, default="clips")
    parser.add_argument("--until", choices=PASSES, default="publish")
    args = parser.parse_args()

    ep = load_episode(args.case)
    start, until = PASSES.index(args.start), PASSES.index(args.until)

    def active(name: str) -> bool:
        return start <= PASSES.index(name) <= until

    if active("clips"):
        if ep.clip_manifest_path.exists() and args.start != "clips":
            print("clips: manifest exists, skipping")
        else:
            print("clips: selecting tape...")
            manifest = select_clips(ep)
            print(f"clips: {len(manifest['clips'])} blocks -> {ep.clip_manifest_path.name}")

    if active("script"):
        manifest = json.loads(ep.clip_manifest_path.read_text())
        if ep.studio_path.exists() and args.start not in ("clips", "script"):
            print("script: studio_events.jsonl exists, skipping")
        else:
            print("script: writing the two-way...")
            studio = write_script(ep, manifest)
            print(f"script: {len(studio)} studio events -> {ep.studio_path.name}")

    if active("tts"):
        print("tts: synthesizing both streams...")
        tts_episode(ep)

    if active("timestamps"):
        print("timestamps: filling clocks + cue sheet...")
        run_timestamp_pass(ep)

    if active("assemble"):
        print("assemble: mixing...")
        assemble(ep)
        assemble_deliberation(ep)

    if active("publish"):
        name = ep.case.get("name", ep.case_id)
        verdict = next((e for e in ep.events if e.get("type") == "verdict"), {})
        reveal = next((e for e in ep.events if e.get("type") == "reveal"), {})
        desc = (f"The panel deliberates {name}. Verdict: {verdict.get('position')} "
                f"{verdict.get('vote_split')}. The real Court: {reveal.get('actual', 'pending')} "
                f"{reveal.get('actual_split', '')}. Every clip is verbatim from the "
                f"deliberation record.")
        print("publish: uploading mp3 + feed...")
        publish_episode(ep, title=name, description=desc)

    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
