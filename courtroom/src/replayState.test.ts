import { describe, expect, it } from "vitest";
import { normalizeEvents, timelineDuration } from "./normalize";
import { replayState } from "./replayState";
import type { DeliberationEvent } from "./types";

// The smoke fixture, verbatim (fixtures/smoke.jsonl) — every event already carries a
// real t, so normalization is a pass-through here and the expected times below are the
// fixture's own numbers.
const SMOKE: DeliberationEvent[] = [
  { t: 0, type: "session_start", case_id: "cl-cluster-99001", round: 0 },
  { t: 500, type: "foreperson", action: "open_session", text: "We are convened on case 24-901.", audio_file: "utt_000.mp3", dur_ms: 7200 },
  { t: 7700, type: "move", agent: "textualist", to: "lectern" },
  { t: 9200, type: "speak", agent: "textualist", round: 1, text: "The statute says 'shall,' not 'may.'", stance: "reverse", confidence: 0.85, audio_file: "utt_001.mp3", dur_ms: 6400 },
  { t: 15600, type: "speak", agent: "pragmatist", round: 1, text: "Every permit issued under the old reading is void.", stance: "affirm", confidence: 0.6, audio_file: "utt_002.mp3", dur_ms: 8100 },
  { t: 23700, type: "vote", agent: "pragmatist", round: 1, position: "affirm", confidence: 0.6, public: false },
  { t: 24200, type: "foreperson", action: "pair_debate", agents: ["textualist", "pragmatist"], text: "Sharpest split on the board.", audio_file: "utt_003.mp3", dur_ms: 6800 },
  { t: 31000, type: "vote_change", agent: "pragmatist", round: 2, from: "affirm", to: "reverse", influenced_by: ["textualist"], reason_text: "The savings clause answers my concern.", audio_file: "utt_004.mp3", dur_ms: 9300 },
  { t: 40300, type: "verdict", position: "reverse", vote_split: "7-2", dissenters: ["living_constitutionalist", "civil_libertarian"] },
  { t: 41000, type: "reveal", actual: "reverse", actual_split: "6-3", match: true },
];

const events = normalizeEvents(SMOKE);

describe("replayState", () => {
  it("t=0: only the session has opened — no positions, votes, speaker or verdict", () => {
    const s = replayState(events, 0);
    expect(s.positions).toEqual({});
    expect(s.votes).toEqual({});
    expect(s.currentSpeaker).toBeNull();
    expect(s.verdict).toBeNull();
  });

  it("mid-speak: the textualist is at the lectern, speaking, stance recorded", () => {
    // 12000ms is inside the textualist utterance (9200–15600).
    const s = replayState(events, 12000);
    expect(s.currentSpeaker).toBe("textualist");
    expect(s.positions.textualist).toBe("lectern");
    expect(s.votes.textualist).toBe("reverse");
    expect(s.verdict).toBeNull();
  });

  it("in the gap between utterances there is no current speaker", () => {
    // The foreperson's open_session ends at 7700; the textualist starts at 9200.
    const s = replayState(events, 8000);
    expect(s.currentSpeaker).toBeNull();
  });

  it("post vote_change: the pragmatist has flipped to reverse and is mid-reason", () => {
    // 32000ms is inside the vote_change utterance (31000–40300).
    const s = replayState(events, 32000);
    expect(s.votes.pragmatist).toBe("reverse");
    expect(s.currentSpeaker).toBe("pragmatist");
    expect(s.verdict).toBeNull();
  });

  it("the pragmatist's stance/vote history resolves to its latest value at each instant", () => {
    expect(replayState(events, 16000).votes.pragmatist).toBe("affirm"); // spoken stance
    expect(replayState(events, 24000).votes.pragmatist).toBe("affirm"); // private vote
    expect(replayState(events, 35000).votes.pragmatist).toBe("reverse"); // after the flip
  });

  it("verdict state: the panel's decision is present once its time passes", () => {
    const s = replayState(events, 41000);
    expect(s.verdict).toEqual({
      position: "reverse",
      vote_split: "7-2",
      dissenters: ["living_constitutionalist", "civil_libertarian"],
    });
    expect(s.currentSpeaker).toBeNull();
  });

  it("t past the end: final state holds and is stable", () => {
    const end = timelineDuration(events);
    const s = replayState(events, end + 500_000);
    expect(s.verdict?.vote_split).toBe("7-2");
    expect(s.positions.textualist).toBe("lectern");
    expect(s.votes.pragmatist).toBe("reverse");
    expect(s.currentSpeaker).toBeNull();
  });

  it("is pure: repeated and out-of-order calls never interfere", () => {
    const a = replayState(events, 12000);
    replayState(events, 40000);
    replayState(events, 0);
    const b = replayState(events, 12000);
    expect(b).toEqual(a);
  });
});

describe("normalizeEvents", () => {
  it("synthesizes a monotonic timeline when t is null", () => {
    const raw: DeliberationEvent[] = [
      { t: null, type: "session_start", case_id: "x", round: 0 },
      { t: null, type: "foreperson", action: "open_session", text: "hi" },
      { t: null, type: "speak", agent: "textualist", round: 1, text: "a".repeat(100), stance: "reverse", confidence: 0.5 },
    ];
    const norm = normalizeEvents(raw);
    expect(norm[0].t).toBe(0);
    // foreperson "hi" → min 3000ms; starts 300 after session_start (dur 0).
    expect(norm[1].t).toBe(300);
    expect(norm[1].durMs).toBe(3000);
    // speak of 100 chars → 100*55 = 5500ms; starts 300 after foreperson ends (300+3000).
    expect(norm[2].t).toBe(3600);
    expect(norm[2].durMs).toBe(5500);
  });
});
