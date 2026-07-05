"""Two-way script pass: anchors' dialogue wrapping the tape -> studio_events.jsonl.

The anchors characterize and analyze; they never re-voice a juror. Tape blocks
enter the stream as `tape_ref` events pointing at clip_manifest spans.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from engine.llm import JUROR_MODEL, chat_json  # noqa: E402
from producer.episode import Episode, speech_text, write_jsonl  # noqa: E402

SCOREBOARD_PATH = REPO_ROOT / "scoreboard" / "results.json"

SYSTEM = """You write the two-anchor script for SPLIT DECISION, a public-radio
style show where two journalists cover an AI jurist panel deliberating real
Supreme Court cases. The panel's nine jurists are AI agents with fixed judicial
philosophies (the Textualist, the Pragmatist, etc.) — the show is transparent
about this; it's part of the premise.

ANCHORS:
- anchor_lead: legal-affairs correspondent. Precise, warm. Explains the LAW —
  facts, procedural posture, what's legally at stake. Public-radio two-way register.
- anchor_analyst: veteran court-watcher. Wry, skeptical. Reads the ROOM —
  personalities, coalition dynamics, who's drifting. Calls flips before they land.
They reference each other by name ("Lead", "counselor" style banter is fine) and
hand off naturally.

HARD RULE (tape integrity): you may characterize what a jurist said, but NEVER
quote more than a 6-word fragment, never paraphrase-as-quote, and never invent
juror dialogue. The tape speaks for itself. Keep the scene descriptions neutral —
describe legal stakes, not any underlying violence.

PLAIN ENGLISH RULE (as hard as the tape rule): write for a listener with ZERO
legal background — a curious teenager should follow every sentence. The jurists
on tape talk like lawyers; the anchors' entire job is translating them. Never
use a legal term without converting it to everyday words in the same breath:
"the county foreclosed — took the house to cover the unpaid taxes", "stare
decisis, the rule that courts stick to what they've decided before". Prefer
plain verbs: "sent back" not "remanded", "threw out" not "vacated", "sided
with" not "concurred". Lead with the human stakes (whose money, whose house,
how much) before any doctrine. After each tape block, the reaction line's first
job is to say what we just heard in plain words.

Write for the ear: short sentences, contractions, no headings, no stage
directions. Numbers read aloud ("nine to nothing", not "9-0")."""


def scoreboard_facts() -> str:
    if not SCOREBOARD_PATH.exists():
        return "No scoreboard yet this season."
    data = json.loads(SCOREBOARD_PATH.read_text())
    facts = []
    for key, label in [("benchmark_wide:A", "solo model"), ("benchmark_wide:B", "silent jury"),
                       ("benchmark:C", "the deliberating panel")]:
        entry = data.get(key) or {}
        if entry.get("accuracy") is not None:
            facts.append(f"{label}: {entry['accuracy']:.1%} correct (n={entry.get('n')})")
    return "; ".join(facts)


def clips_digest(ep: Episode, manifest: dict) -> str:
    lines = []
    for clip in manifest["clips"]:
        start, end = clip["event_span"]
        who = []
        for i in range(start, end + 1):
            ev = ep.events[i]
            tag = f"{ev.get('agent')}"
            if ev.get("type") == "vote_change":
                tag += f" FLIPS {ev.get('from')}->{ev.get('to')}"
            who.append(tag)
        first = speech_text(ep.events[start]) or ""
        last = speech_text(ep.events[end]) or ""
        lines.append(f'{clip["id"]} ({clip["purpose"]}): {" / ".join(who)}. '
                     f'Opens "{first[:90]}..." ends "...{last[-90:]}"')
    return "\n".join(lines)


def build_prompt(ep: Episode, manifest: dict) -> str:
    verdict = next((e for e in ep.events if e.get("type") == "verdict"), {})
    reveal = next((e for e in ep.events if e.get("type") == "reveal"), {})
    case = ep.case
    gt = case.get("ground_truth") or {}
    return f"""EPISODE BRIEF
Case: {case.get('name', ep.case_id)} (docket {case.get('docket', '?')})
Question presented: {case.get('question_presented', 'n/a')}
Facts (plain English): {case.get('facts_summary', 'n/a')}
Panel verdict: {verdict.get('position')} {verdict.get('vote_split')}, dissenters: {', '.join(verdict.get('dissenters', []))}
Real Supreme Court outcome: {reveal.get('actual', gt.get('disposition', 'pending'))} {reveal.get('actual_split', gt.get('vote_split', ''))} — disposition match: {reveal.get('match', 'n/a')}
Season scoreboard (be honest about it): {scoreboard_facts()}

TAPE BLOCKS available (verbatim deliberation audio; play each exactly once, in this order unless a swap clearly helps):
{clips_digest(ep, manifest)}

STRUCTURE (CLAUDE.md §9): cold open = play the cold_open tape FIRST with a one-line
setup at most, then the "...that's the {{jurist}}, moments before..." pull-back and
show intro -> facts two-way (lead explains, analyst raises stakes) -> tape blocks,
each with a 1-3 line anchor setup and a 1-3 line reaction -> verdict (anchors
narrate the five-four reverse, since the verdict moment itself has no tape) ->
reveal: the real Court went nine to nothing the same way — the panel got the
outcome right but read the coalition wrong; let the analyst chew on that ->
season scoreboard check-in (the deliberating panel is LOSING to the silent jury
and the solo model this season — own it, it's interesting) -> outro with a tease
that the panel's rulings on pending cases are on the record.

LENGTH: anchor speech total 900-1300 words (tape carries the rest of the runtime).

Return ONLY JSON, segments in air order:
{{"segments": [
  {{"speaker": "anchor_lead", "text": "..."}},
  {{"tape": "c01"}},
  {{"speaker": "anchor_analyst", "text": "..."}}
]}}"""


def write_script(ep: Episode, manifest: dict) -> list[dict]:
    """Run the script LLM pass; write studio_events.jsonl (t/audio pending)."""
    result = chat_json(JUROR_MODEL, SYSTEM, build_prompt(ep, manifest),
                       purpose="producer:script")
    if not result or not isinstance(result.get("segments"), list):
        raise RuntimeError("script pass returned no usable JSON")

    clips = {c["id"]: c for c in manifest["clips"]}
    studio_events: list[dict] = []
    used: set[str] = set()
    for seg in result["segments"]:
        if isinstance(seg.get("tape"), str):
            clip = clips.get(seg["tape"])
            if not clip or clip["id"] in used:
                print(f"  ! dropping unknown/duplicate tape ref: {seg}")
                continue
            used.add(clip["id"])
            studio_events.append({"t": None, "type": "tape_ref", "clip_id": clip["id"],
                                  "event_span": clip["event_span"], "dur_ms": None})
        elif seg.get("speaker") in ("anchor_lead", "anchor_analyst") and seg.get("text"):
            studio_events.append({"t": None, "type": "studio", "agent": seg["speaker"],
                                  "text": str(seg["text"]).strip(),
                                  "audio_file": None, "dur_ms": None})
    missing = set(clips) - used
    if missing:
        raise RuntimeError(f"script never played tape blocks: {sorted(missing)} — rerun")
    if sum(1 for e in studio_events if e["type"] == "studio") < 8:
        raise RuntimeError("script suspiciously short — rerun")

    # a fresh script obsoletes prior anchor audio; stale files with matching
    # index names would otherwise be silently reused by the TTS pass
    for old in ep.dir.glob("studio_*.mp3"):
        old.unlink()

    write_jsonl(ep.studio_path, studio_events)
    return studio_events
