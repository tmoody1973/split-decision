// The master clock is an interface so the visuals never assume where time comes from.
// Today it's a wall-clock timer (TimerClock). When TTS lands and audio is concatenated,
// AudioClock will drive time from AudioContext.currentTime so audio leads and visuals
// follow — drift-proof — without any change to TimelinePlayer. Same seam, swap the impl.

export interface Clock {
  /** Current playhead position, ms. */
  now(): number;
  start(): void;
  pause(): void;
  /** Jump the playhead; does not change running state. */
  seek(ms: number): void;
  readonly running: boolean;
}

export class TimerClock implements Clock {
  private base = 0; // playhead value captured at the last start/seek
  private startedAt = 0; // performance.now() at the last start
  private _running = false;

  constructor(private readonly source: () => number = () => performance.now()) {}

  now(): number {
    if (!this._running) return this.base;
    return this.base + (this.source() - this.startedAt);
  }

  start(): void {
    if (this._running) return;
    this.startedAt = this.source();
    this._running = true;
  }

  pause(): void {
    if (!this._running) return;
    this.base = this.now();
    this._running = false;
  }

  seek(ms: number): void {
    this.base = ms;
    this.startedAt = this.source();
  }

  get running(): boolean {
    return this._running;
  }
}
