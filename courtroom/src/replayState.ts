import type { NormalizedEvent, ReplayState, Place, Position } from "./types";

// THE deterministic core. Given the full normalized event list and a time t, reconstruct
// the exact stage state — no incremental mutation, no hidden history. seek() is nothing
// more than a call to this. Because it is pure, it is the thing we unit-test hardest.
//
// Rules:
//   positions  — set by `move` events only; every juror defaults to the bench.
//   votes      — last-write-wins across `vote`, `vote_change`, and a speaker's `stance`;
//                a spoken stance IS that juror's current position, so it counts.
//   speaker    — the most recent spoken event (speak/vote_change/foreperson) whose
//                [t, t+durMs) window contains t; null in the gaps between utterances.
//   verdict    — the verdict event once its time has passed.
export function replayState(events: NormalizedEvent[], t: number): ReplayState {
  const positions: Record<string, Place> = {};
  const votes: Record<string, Position | "unknown"> = {};
  let currentSpeaker: string | null = null;
  let verdict: ReplayState["verdict"] = null;

  for (const ev of events) {
    if (ev.t > t) break;

    switch (ev.type) {
      case "move":
        positions[ev.agent] = ev.to;
        break;

      case "vote":
        votes[ev.agent] = ev.position;
        break;

      case "vote_change":
        votes[ev.agent] = ev.to;
        break;

      case "speak":
        votes[ev.agent] = ev.stance;
        break;

      case "verdict":
        verdict = {
          position: ev.position,
          vote_split: ev.vote_split,
          dissenters: ev.dissenters,
        };
        break;

      default:
        break;
    }

    // Speaker is whoever is mid-utterance right now. A finished utterance clears it
    // unless a later one has started.
    if (ev.type === "speak" || ev.type === "vote_change" || ev.type === "foreperson") {
      const speaker = ev.type === "foreperson" ? "foreperson" : ev.agent;
      currentSpeaker = t < ev.t + ev.durMs ? speaker : null;
    }
  }

  return { positions, votes, currentSpeaker, verdict };
}
