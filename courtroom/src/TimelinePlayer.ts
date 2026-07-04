import type { Clock } from "./clock";
import { replayState } from "./replayState";
import { timelineDuration } from "./normalize";
import type { NormalizedEvent, ReplayState } from "./types";

// A timeline VCR — no game logic. It owns the clock and the event list; every frame the
// scene calls tick() to learn the current time, which events were just crossed (for
// one-shot animations like a board flip or a bubble), and whether a seek just happened
// (so consumers rebuild from stateAt() instead of animating). State itself is always
// reconstructed by replayState — the player keeps no incremental state of its own.

export interface Frame {
  now: number;
  crossed: NormalizedEvent[];
  seeked: boolean;
}

export class TimelinePlayer {
  readonly duration: number;
  private lastTick = 0;
  private pendingSeek = false;

  constructor(
    private readonly events: NormalizedEvent[],
    private readonly clock: Clock,
  ) {
    this.duration = timelineDuration(events);
  }

  play(): void {
    if (this.currentTime >= this.duration) this.seek(0);
    this.clock.start();
  }

  pause(): void {
    this.clock.pause();
  }

  toggle(): void {
    if (this.playing) this.pause();
    else this.play();
  }

  seek(ms: number): void {
    const clamped = Math.max(0, Math.min(this.duration, ms));
    this.clock.seek(clamped);
    this.lastTick = clamped;
    this.pendingSeek = true;
  }

  get playing(): boolean {
    return this.clock.running;
  }

  get currentTime(): number {
    return Math.max(0, Math.min(this.duration, this.clock.now()));
  }

  stateAt(t: number): ReplayState {
    return replayState(this.events, t);
  }

  eventsBefore(t: number): NormalizedEvent[] {
    return this.events.filter((ev) => ev.t <= t);
  }

  get allEvents(): NormalizedEvent[] {
    return this.events;
  }

  // The jurist utterance (speak/vote_change) whose window contains t, if any — what the
  // speech bubble should be showing right now.
  activeUtterance(t: number): NormalizedEvent | null {
    let found: NormalizedEvent | null = null;
    for (const ev of this.events) {
      if (ev.t > t) break;
      if (ev.type === "speak" || ev.type === "vote_change") {
        found = t < ev.t + ev.durMs ? ev : null;
      }
    }
    return found;
  }

  // Advance the playhead read. Returns the events whose start time falls in
  // (lastTick, now] — these are "just happened" this frame and should animate once.
  // On a seek we suppress crossings and flag seeked so consumers snap to state instead.
  tick(): Frame {
    const now = this.currentTime;
    if (this.pendingSeek) {
      this.pendingSeek = false;
      this.lastTick = now;
      return { now, crossed: [], seeked: true };
    }

    const from = this.lastTick;
    const crossed = now >= from ? this.events.filter((ev) => ev.t > from && ev.t <= now) : [];
    this.lastTick = now;

    if (this.playing && now >= this.duration) this.clock.pause();

    return { now, crossed, seeked: false };
  }
}
