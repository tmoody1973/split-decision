# Demo video — script & shot list (MOO-227)

**Target: 2:50** (rules cap 3:00). Every beat is aimed at a named judging axis.
Narrator = ElevenLabs VO (production tool; the *product's* voices in the footage are
Qwen TTS — say so in the credits). Composition = Hyperframes (HTML/GSAP), 1920×1080.

Criteria coverage map:
| Beat | Time | Axis served |
|---|---|---|
| Cold open (product tape) | 0:00–0:17 | Presentation — hook |
| The expensive question | 0:17–0:47 | Problem Value 25% |
| How it works (arch diagram) | 0:47–1:12 | Technical Depth 30% |
| Two societies + tape integrity | 1:12–1:38 | Innovation 30% |
| The honest finding | 1:38–2:06 | Depth + Value (the data) |
| Predictions + Plessy | 2:06–2:28 | Value + Innovation |
| Close (prompts public, URL) | 2:28–2:47 | Presentation + Docs |

---

## Beat 1 — COLD OPEN · 0:00–0:17 · no narrator

**Audio:** product tape only — Pung cold open (Textualist vs. Pragmatist clash,
`episodes/cl-cluster-10878534`, clip c01 span). The judges' Qwen voices carry the open.
**Video:** courtroom `?record=1`, bubbles typing, The Record scrolling, vote board live.
**Overlay at 0:14:** freeze-frame, caption: `nine AI judges · real Supreme Court case`

## Beat 2 — THE EXPENSIVE QUESTION · 0:17–0:47

> VO-1: Those aren't voice actors. They're nine AI judges with nine locked judicial
> philosophies, arguing a real Supreme Court case — on the record.

> VO-2: Every team building multi-agent AI pays for the same assumption: that agents
> who debate decide better. Debate is expensive, and almost nobody measures it. So we
> built a full judicial society on Qwen Cloud — and put the assumption itself on trial.

**Video:** slow push on the bench; cut to landing-page hero; title card
`SPLIT DECISION` in the pixel register.

## Beat 3 — HOW IT WORKS · 0:47–1:12 · Technical Depth

> VO-3: One event log is the spine. A clerk on qwen three-seven max writes the bench
> memo. Nine jurists on qwen three-seven plus vote in private before anyone speaks —
> so every changed vote is measurable persuasion, not mimicry. A foreperson pairs the
> sharpest disagreements. The voices are custom-designed in Qwen's voice engine, and
> every API call is cost-logged.

**Video:** the animated PixiJS architecture diagram (capture from the landing page),
with three timed callout pops: `private ballots → measured flips` ·
`qwen3.7-max / qwen3.7-plus routing` · `events.jsonl — one immutable log`.

## Beat 4 — TWO SOCIETIES, ONE RECORD · 1:12–1:38 · Innovation

> VO-4: Then a second society covers the first. Two AI journalists cut each
> deliberation into a podcast. The hard rule: they can frame the tape, but they can
> never rewrite a word of it. After every episode we diff the record — zero changes,
> every time. Agents holding agents accountable.

**Video:** podcast mode — anchors at the news desk, hard cut into courtroom tape,
The Record showing navy STUDIO lines between verbatim tape lines. Overlay:
`tape integrity: 0 content diffs / 193 events`.

## Beat 5 — THE HONEST FINDING · 1:38–2:06 · the data

> VO-5: Here's what the measurement said. One model, asked directly: eighty-three
> percent against the real Court. Nine judges voting in silence: seventy-seven. The
> full deliberating society: sixty-six point seven. Debate made them worse — eloquent
> majorities talked correct votes into five-to-four splits on cases the real Court
> decided nine to nothing. We published that instead of hiding it.

**Video:** rebuild the three bars natively in Hyperframes (crisper than capture),
gold on dark, 83 → 77.4 → 66.7 animating in sequence; the last bar lands with a
thud + dims. Caption: `the measured cost of debate: −10.7 points`.

## Beat 6 — SKIN IN THE GAME · 2:06–2:28 · Value

> VO-6: Three predictions now sit on the record for cases the Court hasn't decided —
> we will be graded in public, whether we like it or not. And in a labeled exhibition,
> we gave the panel Plessy versus Ferguson. It reproduced eighteen ninety-six. Only
> the two rights-first philosophies said no. Method is never neutral.

**Video:** picker showing `Predictions on the Record`; cut to Plessy courtroom with
the EXHIBITION badge; vote board 7–2 with the two dissent tiles highlighted.

## Beat 7 — CLOSE · 2:28–2:47

> VO-7: Every agent's full prompt is public. Every episode replays from the log.
> Split Decision — two agent societies, one immutable record. Built on Qwen Cloud.

**Video:** prompt modal flash (Textualist's "you change your vote ONLY when…" line
highlighted) → landing page → end card: URL, GitHub, `Track 3 · Agent Society`,
`voices: Qwen TTS · narrator: ElevenLabs`.

---

## Production notes

- **Captures** (1080p, `?record=1`): courtroom Pung cold open; podcast-mode desk→tape
  cut (~1:50–2:40 of the Pung podcast); Plessy verdict moment; landing hero + diagram
  + prompt modal. Capture AFTER final UI sign-off.
- **VO:** `scripts/make_demo_vo.py` extracts the `VO-n` blocks above and renders
  ElevenLabs MP3s to `video/vo/` (voice via `ELEVENLABS_VOICE_ID`, default Daniel).
- **Hyperframes:** project in `video/` — design.md mirrors the app palette
  (`#1a140d/#f0d79a/#caa24a/#7a1f2b/#1e2a4a`, ui-monospace). Rhythm:
  TAPE-fast-DIAGRAM-hold-CUT-fast-BARS-slow-hold-CLOSE.
- Product tape segments keep their own audio (Qwen voices); narrator ducks out.
