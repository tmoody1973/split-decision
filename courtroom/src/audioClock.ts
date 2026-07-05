import type { Clock } from "./clock";

// The real master clock: a single pre-rendered deliberation.mp3 whose timeline IS the
// replay clock (the Producer places every utterance at its event `t`, same 300ms gaps).
// audio.currentTime is therefore the playhead — visuals follow audio, never the reverse,
// so sync cannot drift. Same Clock seam as TimerClock; TimelinePlayer is unchanged.
export class AudioClock implements Clock {
  constructor(private readonly audio: HTMLAudioElement) {}

  now(): number {
    return this.audio.currentTime * 1000;
  }

  start(): void {
    // play() is async and may be rejected by autoplay policy before any user gesture —
    // report it and stay paused rather than throwing from a sync call site.
    void this.audio.play().catch((err) => console.warn("audio play blocked:", err));
  }

  pause(): void {
    this.audio.pause();
  }

  seek(ms: number): void {
    this.audio.currentTime = ms / 1000;
  }

  get running(): boolean {
    return !this.audio.paused && !this.audio.ended;
  }
}

/** Probe for an episode's pre-rendered replay track; null if it doesn't exist. */
export async function loadEpisodeAudio(episodeId: string): Promise<HTMLAudioElement | null> {
  const url = `episodes/${episodeId}/deliberation.mp3`;
  const head = await fetch(url, { method: "HEAD" }).catch(() => null);
  // Dev/preview servers SPA-fallback missing files to index.html with a 200 —
  // only a real audio content-type counts as "this episode ships audio".
  const type = head?.headers.get("content-type") ?? "";
  if (!head?.ok || !type.startsWith("audio")) return null;
  const audio = new Audio(url);
  audio.preload = "auto";
  return audio;
}
