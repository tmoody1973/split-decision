"""Timestamp pass: fill `t` on both streams, write cue_sheet.json.

Two clocks (PRD decision):
- events.jsonl `t`  = courtroom replay clock: all deliberation utterances
  concatenated in sequence order with 300ms gaps (the Phaser VCR's timeline).
- studio_events.jsonl `t` = podcast clock: studio segments in order; each
  tape_ref expands to its span's utterances, also 300ms-gapped.
The cue sheet is the PODCAST view spanning both streams; its `t` values are
podcast-clock for every entry (deliberation entries included).
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from producer.episode import GAP_MS, Episode, read_jsonl, write_jsonl  # noqa: E402


def fill_replay_clock(events: list[dict]) -> list[dict]:
    """Courtroom clock: every event gets a t; speech advances the cursor."""
    out, cursor = [], 0
    for ev in events:
        stamped = {**ev, "t": cursor}
        out.append(stamped)
        if stamped.get("dur_ms"):
            cursor += int(stamped["dur_ms"]) + GAP_MS
    return out


def fill_podcast_clock(studio: list[dict], events: list[dict]) -> tuple[list[dict], list[dict]]:
    """Podcast clock: returns (stamped studio events, cue sheet rows)."""
    stamped, cues, cursor = [], [], 0
    for ev in studio:
        if ev["type"] == "studio":
            row = {**ev, "t": cursor}
            stamped.append(row)
            cues.append({"t": cursor, "stream": "studio",
                         "event_index": len(stamped) - 1,
                         "audio_file": row["audio_file"], "dur_ms": row["dur_ms"]})
            cursor += int(row["dur_ms"]) + GAP_MS
        elif ev["type"] == "tape_ref":
            start, end = ev["event_span"]
            block_start = cursor
            for i in range(start, end + 1):
                dev = events[i]
                if not dev.get("dur_ms"):
                    continue  # non-audio event inside a span (defensive)
                cues.append({"t": cursor, "stream": "deliberation", "event_index": i,
                             "audio_file": dev["audio_file"], "dur_ms": dev["dur_ms"]})
                cursor += int(dev["dur_ms"]) + GAP_MS
            stamped.append({**ev, "t": block_start, "dur_ms": cursor - GAP_MS - block_start})
        else:
            stamped.append({**ev, "t": cursor})
    return stamped, cues


def run_timestamp_pass(ep: Episode) -> list[dict]:
    events = fill_replay_clock(read_jsonl(ep.events_path))
    write_jsonl(ep.events_path, events)

    if not ep.studio_path.exists():
        print("no studio stream — replay clock filled, no cue sheet")
        return []
    studio, cues = fill_podcast_clock(read_jsonl(ep.studio_path), events)
    write_jsonl(ep.studio_path, studio)
    ep.cue_sheet_path.write_text(json.dumps(cues, indent=1) + "\n")
    total_min = (cues[-1]["t"] + cues[-1]["dur_ms"]) / 60000 if cues else 0
    print(f"cue sheet: {len(cues)} entries, runtime {total_min:.1f} min")
    return cues
