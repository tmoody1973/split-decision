import type { DeliberationEvent, NormalizedEvent } from "./types";

// Producer-quality timing isn't available yet: real episodes ship with t=null on every
// event (the Producer fills them after TTS). Until then we synthesize a playable
// timeline — each event starts 300ms after the previous one ends; spoken events last
// max(3000, chars * 55) ms. Events that already carry a real t (e.g. the smoke fixture)
// are honoured as-is. This is the ONE place timing is invented; everything downstream
// reads concrete numbers.

const GAP_MS = 300;
const MIN_SPEAK_MS = 3000;
const MS_PER_CHAR = 55;

function textOf(ev: DeliberationEvent): string {
  if (ev.type === "speak") return ev.text;
  if (ev.type === "vote_change") return ev.reason_text;
  if (ev.type === "foreperson") return ev.text;
  return "";
}

function isSpoken(ev: DeliberationEvent): boolean {
  return ev.type === "speak" || ev.type === "vote_change" || ev.type === "foreperson";
}

function synthDuration(ev: DeliberationEvent): number {
  if (!isSpoken(ev)) return 0;
  const declared = (ev as { dur_ms?: number }).dur_ms;
  if (typeof declared === "number" && declared > 0) return declared;
  return Math.max(MIN_SPEAK_MS, textOf(ev).length * MS_PER_CHAR);
}

export function normalizeEvents(events: DeliberationEvent[]): NormalizedEvent[] {
  const out: NormalizedEvent[] = [];
  let cursor = 0;

  events.forEach((ev, index) => {
    const durMs = synthDuration(ev);
    let t: number;
    if (typeof ev.t === "number") {
      t = ev.t;
    } else if (index === 0) {
      t = 0;
    } else {
      t = cursor + GAP_MS;
    }
    cursor = Math.max(cursor, t + durMs);
    out.push({ ...(ev as DeliberationEvent), t, durMs, index } as NormalizedEvent);
  });

  return out;
}

export function timelineDuration(events: NormalizedEvent[]): number {
  return events.reduce((max, ev) => Math.max(max, ev.t + ev.durMs), 0);
}

// Parse a .jsonl blob, dropping blank lines. Studio-stream events (studio/tape_ref) are
// filtered out — the courtroom renders the deliberation record only.
export function parseJsonl(raw: string): DeliberationEvent[] {
  return raw
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as DeliberationEvent)
    .filter((ev) => ev.type !== ("studio" as unknown) && ev.type !== ("tape_ref" as unknown));
}
