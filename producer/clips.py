"""Clip selection pass: transcript -> clip_manifest.json (event-index spans only).

TAPE INTEGRITY: the model picks WHERE the tape starts and ends (0-based event
indices into events.jsonl); it never returns rewritten text. Anything textual
in its output is discarded except short producer notes.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.llm import JUROR_MODEL, chat_json  # noqa: E402
from producer.episode import Episode, speech_text  # noqa: E402

SYSTEM = """You are the tape producer for SPLIT DECISION, a podcast where two
journalists cover an AI jurist panel deliberating real Supreme Court cases.
You select which stretches of the deliberation recording become tape blocks.
You NEVER rewrite or paraphrase what was said — you only choose spans of
event indices. Pick tape that is sharp, argumentative, and self-contained."""


def numbered_transcript(events: list[dict]) -> str:
    lines = []
    for i, ev in enumerate(events):
        etype = ev.get("type")
        text = speech_text(ev)
        if text:
            who = ev.get("agent", "?")
            extra = ""
            if etype == "vote_change":
                extra = f" [FLIP {ev.get('from')}->{ev.get('to')}]"
            lines.append(f"[{i}] r{ev.get('round', '?')} {who}{extra} ({etype}): {text}")
        elif etype == "verdict":
            lines.append(f"[{i}] VERDICT: {ev.get('position')} {ev.get('vote_split')} "
                         f"(dissenting: {', '.join(ev.get('dissenters', []))})")
        elif etype == "reveal":
            lines.append(f"[{i}] REVEAL: actual {ev.get('actual')} {ev.get('actual_split')} "
                         f"match={ev.get('match')}")
    return "\n".join(lines)


def build_prompt(ep: Episode) -> str:
    return f"""Case: {ep.case.get('name', ep.case_id)}

Below is the full deliberation, one event per line, prefixed by its 0-based
event index in brackets. Only lines shown carry audio-able speech (plus the
VERDICT/REVEAL markers, which have no audio — never include them in a span).

Select 6-10 tape blocks for a 12-18 minute episode:
- "cold_open": the single sharpest 1-3 event exchange in the whole deliberation
- one block per major vote flip, INCLUDING the 1-3 events that triggered it
  (the persuasion, then the [FLIP] event itself)
- "verdict_run": the final exchange just before the verdict (speech events only)

Rules:
- A span is [start_index, end_index], inclusive, 1 to 6 events long.
- Spans must only cover indices that appear below (speech events).
- Blocks must not overlap. Order them as they should air.
- Total tape budget: spans totalling 25-40 events across all blocks.

Return ONLY JSON:
{{"clips": [{{"id": "c01", "purpose": "cold_open|flip|verdict_run|color",
  "event_span": [start, end], "note": "<=15 words why this tape"}}]}}

DELIBERATION:
{numbered_transcript(ep.events)}"""


def _valid_span(span: object, ep: Episode) -> bool:
    if not (isinstance(span, list) and len(span) == 2):
        return False
    start, end = span
    if not (isinstance(start, int) and isinstance(end, int)):
        return False
    if not (0 <= start <= end < len(ep.events) and end - start < 6):
        return False
    return all(speech_text(ep.events[i]) for i in range(start, end + 1))


def select_clips(ep: Episode) -> dict:
    """Run the clip-selection LLM pass and write clip_manifest.json."""
    result = chat_json(JUROR_MODEL, SYSTEM, build_prompt(ep), purpose="producer:clips")
    if not result or not isinstance(result.get("clips"), list):
        raise RuntimeError("clip selection returned no usable JSON")

    clips, seen = [], set()
    for idx, clip in enumerate(result["clips"]):
        span = clip.get("event_span")
        if not _valid_span(span, ep):
            print(f"  ! dropping clip with bad span: {clip}")
            continue
        if any(i in seen for i in range(span[0], span[1] + 1)):
            print(f"  ! dropping overlapping clip: {clip}")
            continue
        seen.update(range(span[0], span[1] + 1))
        clips.append({
            "id": f"c{idx + 1:02d}",
            "purpose": str(clip.get("purpose", "color")),
            "event_span": [span[0], span[1]],
            "note": str(clip.get("note", ""))[:120],
        })
    if len(clips) < 4:
        raise RuntimeError(f"only {len(clips)} valid clips selected — rerun")

    manifest = {"case_id": ep.case_id, "clips": clips}
    ep.clip_manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
