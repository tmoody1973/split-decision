# Handoff: Hyperframes demo-video composition (MOO-248)

For a fresh session assembling the final judged demo MP4. Track work on Linear
**MOO-248** (pre-production evidence is in its comments). The spec you are
implementing is **docs/video/demo-script.md** — beat timings, VO text, shot list,
criteria coverage map. Do not re-decide the script; it is signed off.

## Skills to load (in this order)

1. `/hyperframes` — then its ALWAYS-READ refs for a multi-scene piece:
   `references/video-composition.md`, `references/beat-direction.md`,
   `references/typography.md`, `references/motion-principles.md`,
   `references/transitions.md`, plus `references/narration.md` and
   `data-in-motion.md` (the findings-bars scene is native, not captured).
2. `/gsap` if animation patterns are needed beyond the refs.

## What exists (don't rebuild)

- **Narration** — `video/vo/vo_1.mp3 … vo_7.mp3`, approved voice. Durations:
  | cue | s | | cue | s |
  |---|---|---|---|---|
  | VO-1 | 9.1 | | VO-5 | 24.1 |
  | VO-2 | 17.0 | | VO-6 | 19.8 |
  | VO-3 | 24.7 | | VO-7 | 10.6 |
  | VO-4 | 18.9 | | total | 124.3 |
- **Captures** (1920×1080 30fps h264, silent by design) in `video/captures/`:
  - `pung-podcast.mp4` (175s): ~0:00–0:04 desk setup line → **0:04–1:47 courtroom
    with tape playing** (beat-1 footage) → **1:47–2:55 news desk** with navy STUDIO
    lines scrolling in The Record (beat-4 footage). Exact tape offsets: read
    `episodes/cl-cluster-10878534/cue_sheet.json` (podcast clock, authoritative).
  - `plessy-verdict.mp4` (55s): EXHIBITION badge, 7–2 board, verdict lands late in
    the clip; the Record shows the Textualist/Civil-Libertarian exchange (beat 6).
  - `landing-tour.mp4` (42s): 0–4 hero → ~5–13 scroll to live PixiJS diagram →
    13–22 animated dots → 22–26 agent grid → 26–34 Textualist prompt modal (beat 7).
  - Regenerate any capture with `node video/capture.mjs` (vite preview must be
    serving `courtroom/dist` on :4173 — `cd courtroom && npm run preview`).
- **Product audio for tape segments** — `episodes/cl-cluster-10878534/episode.mp3`
  (the mixed podcast). The captures were driven by this exact file (AudioClock),
  so aligning `data-media-start` to the capture's seek offset gives perfect sync.
  Beat 1 wants episode audio from ~4.7s (start of tape c01; verify in cue_sheet).
- **VO pipeline** — `scripts/make_demo_vo.py` re-renders narration if the script
  doc's `> VO-n:` blocks change (voice ID locked in the doc).

## Design tokens (the app's pixel register — make design.md from these)

- Palette: bg `#1a140d`, panel `#241a10`, line `#4a3320`, wood `#8a5a2b`,
  ink `#e8e0d2`, muted `#9a8f7d`, gold `#caa24a`, gold-hi `#f0d79a`,
  navy `#1e2a4a`/`#3a5a9a`, burgundy `#7a1f2b`, green `#3f6d4e`.
- Type: `ui-monospace, Menlo, monospace`, bold, letter-spaced smallcaps-style labels.
- Shape language: 3px hard borders, hard offset shadows (`4px 4px 0 #000a`),
  colored header bars, `image-rendering: pixelated` on any product imagery.
  Reference implementations: `courtroom/findings.html`, `courtroom/index.html`
  (landing), `courtroom/src/archDiagram.ts` (drawPixelBox).
- Declared rhythm (already in the spec): TAPE-fast-DIAGRAM-hold-CUT-fast-BARS-slow-hold-CLOSE.

## Field knowledge (hard-won, trust these)

- Captures carry **no audio on purpose** — lay `episode.mp3` (tape beats) and
  `vo_n.mp3` (narration) as separate `<audio>` clips; duck nothing over the cold
  open (VO silent there per spec).
- The findings-bars beat (beat 5) is built **natively** in HTML/GSAP, not captured
  — numbers: 83 / 77.4 / 66.7, n=94/93/24, "−10.7 points" caption. Follow
  `data-in-motion.md`; 0-based bars, gold on dark, last bar dims.
- Hyperframes non-negotiables that bit elsewhere: every timeline
  `{paused:true}` + registered on `window.__timelines`; video elements
  `muted playsinline` with audio as separate elements; no `repeat:-1`; no exit
  animations except final scene — transitions handle exits; build layout at the
  hero frame FIRST, then `gsap.from()` entrances.
- End card must credit: `voices: Qwen TTS · narrator: ElevenLabs`, the GitHub URL
  (github.com/tmoody1973/split-decision), `Track 3 · Agent Society`.
- Rules cap: **3:00 hard**. The spec targets 2:50.

## Definition of done (MOO-248 checklist)

`npx hyperframes lint` + `validate` + `inspect` clean (mark intentional
overflows), animation-map reviewed, final MP4 rendered ≤3:00, Tarik watches and
approves, then check off MOO-248 and comment with the render path + runtime.

## Out of scope for that session

SAS deploy + proof screenshot (MOO-226, needs Tarik in the Alibaba console);
publishing landmark/pending episodes to the RSS feed (hero pick pending);
README/blog/Devpost (MOO-227).
