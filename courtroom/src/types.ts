// Event shapes mirror contracts/events.schema.json. The renderer only consumes the
// deliberation stream (session_start/speak/vote/vote_change/foreperson/move/verdict/reveal);
// studio/tape_ref belong to the separate studio stream and are ignored here.

export type Position = "affirm" | "reverse";
export type Place = "bench" | "lectern" | "huddle";

export type JuristId =
  | "textualist"
  | "originalist"
  | "living_constitutionalist"
  | "pragmatist"
  | "precedent_maximalist"
  | "federalism_hawk"
  | "civil_libertarian"
  | "process_formalist"
  | "minimalist";

export interface SessionStartEvent {
  t: number | null;
  type: "session_start";
  case_id: string;
  round: 0;
}

export interface SpeakEvent {
  t: number | null;
  type: "speak";
  agent: JuristId;
  round: number;
  text: string;
  stance: Position;
  confidence: number;
  synthesized?: boolean; // text is an engine placeholder after a malformed reply
  audio_file?: string;
  dur_ms?: number;
}

export interface VoteEvent {
  t: number | null;
  type: "vote";
  agent: JuristId;
  round: number;
  position: Position;
  confidence: number;
  public: false;
  synthesized?: boolean; // engine carried a prior position forward on a malformed reply
}

export interface VoteChangeEvent {
  t: number | null;
  type: "vote_change";
  agent: JuristId;
  round: number;
  from: Position;
  to: Position;
  influenced_by: JuristId[];
  reason_text: string;
  influence_inferred?: boolean; // influenced_by inferred by the engine, not named by the jurist
  reason_inferred?: boolean; // reason_text is an engine placeholder, not the jurist's words
  audio_file?: string;
  dur_ms?: number;
}

export interface ForepersonEvent {
  t: number | null;
  type: "foreperson";
  action: string;
  agents?: JuristId[];
  text: string;
  audio_file?: string;
  dur_ms?: number;
}

export interface MoveEvent {
  t: number | null;
  type: "move";
  agent: JuristId;
  to: Place;
}

export interface VerdictEvent {
  t: number | null;
  type: "verdict";
  position: Position;
  vote_split: string;
  dissenters: JuristId[];
}

export interface RevealEvent {
  t: number | null;
  type: "reveal";
  actual: Position;
  actual_split: string;
  match: boolean;
}

// Studio stream (podcast mode): anchor commentary. tape_ref events are resolved by the
// cue sheet into deliberation spans and never reach the renderer directly.
export interface StudioEvent {
  t: number | null;
  type: "studio";
  agent: "anchor_lead" | "anchor_analyst";
  text: string;
  audio_file?: string;
  dur_ms?: number;
}

export type DeliberationEvent =
  | SessionStartEvent
  | SpeakEvent
  | VoteEvent
  | VoteChangeEvent
  | ForepersonEvent
  | MoveEvent
  | VerdictEvent
  | RevealEvent
  | StudioEvent;

// After normalization every event carries a concrete start time and a visual/audio
// duration (0 for instantaneous events). `index` is the original line index — the
// unit The Record and tape_refs address clips by.
export type NormalizedEvent = DeliberationEvent & {
  t: number;
  durMs: number;
  index: number;
};

export interface VerdictState {
  position: Position;
  vote_split: string;
  dissenters: JuristId[];
}

// The full reconstructable state at any instant — the sole thing seek() depends on.
export interface ReplayState {
  positions: Record<string, Place>;
  votes: Record<string, Position | "unknown">;
  currentSpeaker: string | null;
  verdict: VerdictState | null;
}
