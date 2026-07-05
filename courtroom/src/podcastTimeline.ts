import type { DeliberationEvent, NormalizedEvent } from "./types";
import { normalizeEvents } from "./normalize";

// Podcast mode's data layer. The cue sheet is the authority (contract: the player never
// re-derives timing): each row points into one of the two streams by raw line index and
// carries the podcast-clock `t`. From it we build:
//   merged      — the podcast timeline the player runs on (studio + aired tape events)
//   stateEvents — the FULL deliberation on its replay clock, for vote-board state
//   streamAt    — which set the camera shows at a podcast instant
//   sceneTime   — podcast clock -> replay clock (so the courtroom shows the exact
//                 deliberation moment the aired tape came from)

interface CueRow {
  t: number;
  stream: "deliberation" | "studio";
  event_index: number;
  audio_file: string;
  dur_ms: number;
}

export interface PodcastTimeline {
  merged: NormalizedEvent[];
  stateEvents: NormalizedEvent[];
  streamAt: (t: number) => "studio" | "deliberation";
  sceneTime: (t: number) => number;
  duration: number;
}

function parseRawJsonl(raw: string): DeliberationEvent[] {
  // Raw line order preserved — cue_sheet event_index addresses lines, so nothing
  // may be filtered here (unlike the courtroom-mode parser).
  return raw
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as DeliberationEvent);
}

export async function loadPodcastTimeline(episodeId: string): Promise<PodcastTimeline | null> {
  const get = async (file: string): Promise<string | null> => {
    const res = await fetch(`episodes/${episodeId}/${file}`).catch(() => null);
    const type = res?.headers.get("content-type") ?? "";
    return res?.ok && !type.includes("html") ? res.text() : null;
  };
  const [cuesRaw, eventsRaw, studioRaw] = await Promise.all([
    get("cue_sheet.json"), get("events.jsonl"), get("studio_events.jsonl"),
  ]);
  if (!cuesRaw || !eventsRaw || !studioRaw) return null;

  const cues = JSON.parse(cuesRaw) as CueRow[];
  const delib = parseRawJsonl(eventsRaw);
  const studio = parseRawJsonl(studioRaw);
  const stateEvents = normalizeEvents(delib);

  const merged: NormalizedEvent[] = cues.map((cue, i) => {
    const source = cue.stream === "studio" ? studio[cue.event_index] : delib[cue.event_index];
    return { ...source, t: cue.t, durMs: cue.dur_ms, index: i } as NormalizedEvent;
  });

  // Per-cue mapping into the replay clock (deliberation rows only).
  const spans = cues.map((cue) => ({
    start: cue.t,
    end: cue.t + cue.dur_ms,
    stream: cue.stream,
    replayStart: cue.stream === "deliberation" ? (stateEvents[cue.event_index]?.t ?? 0) : 0,
  }));

  const streamAt = (t: number): "studio" | "deliberation" => {
    let current: "studio" | "deliberation" = "studio";
    for (const s of spans) {
      if (s.start > t) break;
      current = s.stream;
    }
    return current;
  };

  const sceneTime = (t: number): number => {
    let mapped = 0;
    for (const s of spans) {
      if (s.stream !== "deliberation") continue;
      if (t >= s.end) mapped = s.replayStart + (s.end - s.start);
      else if (t >= s.start) return s.replayStart + (t - s.start);
      else break;
    }
    return mapped;
  };

  const last = cues[cues.length - 1];
  return { merged, stateEvents, streamAt, sceneTime, duration: last.t + last.dur_ms };
}
