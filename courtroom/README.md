# Courtroom — the pixel replay player

A deterministic VCR over a deliberation's `events.jsonl`. No game logic: it reconstructs
stage state from the event log at any instant and renders it. When an episode ships a
Producer-rendered `deliberation.mp3`, audio drives the clock (`audioClock.ts` — 
audio.currentTime IS the playhead, drift-proof); episodes without audio fall back to a
wall-clock timer with synthesized timing.

## Run

```bash
npm install
npm run dev        # runs sync-assets first, then Vite
```

- `?episode=cl-cluster-10878534` (default) — the real 193-event deliberation
- `?episode=smoke` — the 10-event hand-written fixture
- `?record=1` — hides controls and autoplays for 1080p screen capture (the split view IS
  the demo video)

```bash
npm test           # vitest — the replayState unit tests
npm run build      # tsc --noEmit + vite build -> dist/
```

## Assets are synced, not authored here

`scripts/sync-assets.mjs` copies the shared source-of-truth files into `public/` (which is
git-ignored) before every dev/build:

- `episodes/cl-cluster-10878534/events.jsonl` ← repo `episodes/…`
- `episodes/smoke/events.jsonl` ← repo `fixtures/smoke.jsonl`
- `assets/sprites/*` ← repo `assets/sprites/`

The courtroom is a *consumer* of the same log the scoreboard and producer read; this
script is the only bridge and it copies, never edits.

## Timing note

Produced episodes (e.g. Pung) carry real Producer timestamps and a `deliberation.mp3`;
the rest still ship `t: null`. For those, `normalize.ts` synthesizes a playable timeline: each event starts 300ms
after the previous ends, spoken events last `max(3000, chars × 55)` ms. Events that
already carry a real `t` (the smoke fixture) are honoured as-is. This is the one place
timing is invented.

## Architecture

- `replayState.ts` — **pure** `(events, t) => state`. The tested core; `seek()` is just a
  call to it. State = positions, votes, current speaker, verdict.
- `normalize.ts` — assigns concrete `t`/duration to every event; parses `.jsonl`.
- `clock.ts` / `audioClock.ts` — the `Clock` seam: `AudioClock` (audio-driven master
  clock) when the episode has a replay track, `TimerClock` otherwise.
- `TimelinePlayer.ts` — owns clock + events; `tick()` reports the time, freshly-crossed
  events (one-shot animations), and whether a seek just happened (snap vs animate).
- `CourtScene.ts` — Phaser scene; reconstructs state each frame and drives visuals.
- `Stage / JuristSprite / VoteBoard / Bubble` — Phaser presentation. All nine jurists
  use real sprite sheets, seated behind the painted bench (a cropped bench-front
  overlay occludes their lower bodies; feet are pixel-scanned to the baseline).
- `RecordPanel.ts` — "The Record" DOM transcript (right 35%). Lines append as events play,
  `vote_change` renders as a highlighted system line, click-to-seek, running tally,
  auto-scroll with pause-on-hover.
