# ⚖️ Split Decision

> Nine AI jurists with distinct judicial philosophies deliberate real Supreme Court
> cases — arguing, persuading, and flipping votes — while an AI newsroom turns every
> deliberation into a podcast and a pixel-art courtroom replay. The panel's
> predictions are scored against the real Court, including cases it hasn't decided yet.

Built for the **Qwen Cloud Global AI Hackathon — Track 3: Agent Society** ·
Submission July 8, 2026 · Solo build by [Tarik Moody](https://github.com/tmoody1973)

> ⚖️ **Live now:** [split-decision.tarikmoody.com](https://split-decision.tarikmoody.com) —
> courtroom replays, [findings](https://split-decision.tarikmoody.com/findings.html),
> [live bench](https://split-decision.tarikmoody.com/live.html),
> [judge's tour](https://split-decision.tarikmoody.com/judges.html), and the
> [podcast feed](https://split-decision.tarikmoody.com/feed.xml). Runs on Alibaba
> Cloud (SAS, Singapore). Submission: July 8, 2026. Blueprint:
> [CLAUDE.md](CLAUDE.md) · Product spec: [docs/PRD.md](docs/PRD.md)

## The core question

Teams shipping multi-agent systems can't answer the most expensive question in the
pattern: **does deliberation actually improve decisions, or just multiply inference
cost?** Split Decision measures it on one of the few public corpora of genuinely
hard, formally adjudicated judgment calls — Supreme Court outcomes — with free,
authoritative ground truth.

Three conditions, identical case records:

| Condition | Setup | Cost |
|---|---|---|
| **A. Solo** | One `qwen3.7-max` call predicts disposition + vote split | 1 call |
| **B. Silent jury** | 9 philosophically distinct jurists vote independently, majority wins | 9 calls |
| **C. Society** | Full structured deliberation: private votes → statements → paired debate → revotes, up to 5 rounds | ~150 calls |

**C − B is the value of deliberation itself** — the headline number. A null or
negative result gets reported honestly as a finding.

## Results (first full run July 5, 2026; paired analysis July 6)

**Paired comparison — all conditions graded on the identical 24 post-cutoff
cases** (the only honest way to compare; an earlier version of this table
compared C against B on a different, larger pool):

| Condition | Accuracy (same 24 cases) | 95% CI |
|---|---|---|
| Always-guess-"reverse" baseline | 75.0% | — |
| A — solo `qwen3.7-max` | 75.0% | 55.1–88.0% |
| B — silent jury of 9 | 66.7% | 46.7–82.0% |
| C — full deliberation (9 ideologues) | 66.7% | 46.7–82.0% |
| C-neutral — full deliberation (9 neutral analysts, control) | 66.7% | 46.7–82.0% |

C vs B paired sign test: debate corrected 2 cases and spoiled 2 (p = 1.0) —
**deliberation was accuracy-neutral**, not accuracy-negative. Full-pool numbers
(different n, listed for completeness, never compared against C): baseline
72.3%, A 83.0% (n=94), B 77.4% (n=93); famous landmarks A/B 95.8%, ordinary
historical A 96.0% / B 100%.

Three measured findings, reproducible via `scripts/run_benchmark.py --aggregate`
from the committed per-case predictions:

1. **Contamination is ~15 points and reaches obscure cases.** The model scores
   96–100% on *anything* pre-cutoff — even cases no law student has heard of —
   vs 77–83% on post-cutoff cases. Benchmarks on historical rulings are
   measuring memory, not judgment.
2. **Deliberation moved persuasion, not accuracy — and nothing beat the naive
   baseline on the sample.** Paired on identical cases, silent and debating
   juries both scored 66.7%; the 85 argued vote changes redistributed errors
   (2 fixed, 2 broken) without reducing them. On these 24 brand-new cases no
   condition beat "always guess reverse" (75%), though solo does clear that
   bar on the full 94-case pool (83.0% vs 72.3%). Our first published readout
   claimed debate cost 10 points; that was an unpaired-pool artifact, and the
   correction is part of the exhibit.
3. **Steerability follows philosophy.** Flip counts per juror: Minimalist 21,
   Pragmatist 14, Precedent Maximalist 13 … Originalist 1, Textualist 1. The
   archetypes anchored to fixed sources (text, history) are nearly immovable;
   the ones anchored to case-by-case judgment sway constantly.
4. **The personas aren't the ceiling — a neutral control panel scored the
   same.** Nine neutral analysts (no ideology, flip trigger = "a better
   argument") ran the identical protocol on the identical 24 cases: 66.7%,
   exactly matching the ideologue panel (the two disagreed on 4 cases and
   split them 2–2). What changed was character, not accuracy: neutral panels
   converged in ~1.5 rounds vs ~2.9, flipped 62 times vs 85 with no
   philosophy gradient (5–11 flips per juror vs 1–21), reached unanimous 9–0
   verdicts on half the cases, and tracked the real Court's vote splits
   better (split distance 1.4 vs 2.4, n=5). Ideology shapes the debate;
   the model sets the score.

Deliberation makes equally accurate predictions and much better arguments —
which is the honest trade this project set out to measure. (One of 25
deliberation cases failed on a content-moderation block and is excluded;
per-case predictions live in `scoreboard/predictions/`. Split-distance stats
carry their own `split_n` — only 3 of the 24 sample cases have a known real
vote split.)

### Contamination guard (and the memorization exhibit)

Benchmark cases are decided **after 2025-06-01** — past every model's training
cutoff — plus argued-but-undecided cases where the panel's prediction goes on the
record before reality answers. A two-tier **memorization-check arm** (25 famous
landmarks + 25 ordinary historical cases, identical minimal inputs) quantifies
exactly how much training-data recall would have contaminated a naive benchmark.

### Anti-sycophancy machinery

Multi-agent panels collapse into consensus by default. The chamber resists it
structurally:

- **Private scratchpad votes before public statements** every round — positions
  form independently; persuasion becomes measurable, not mimicry
- **Persona re-injection every round** — drift resistance
- **Per-philosophy flip triggers** — each jurist changes its vote *only* on the
  kind of argument its philosophy credits (text, history, consequences, precedent…)
- **Foreperson structurally barred** from stating a merits position
- **Per-juror memory digests** written from each jurist's own perspective, not a
  shared neutral summary

### Tape integrity rule

Every podcast clip is verbatim from `events.jsonl` — the same immutable,
schema-validated event log that feeds the scoreboard, the courtroom renderer, and
the transcript panel. The journalist anchors characterize and analyze; they never
rewrite the record. One log, four consumers.

**Degraded data is marked, never silent.** When a jurist's reply is malformed,
the engine carries its prior position forward and stamps the vote event
`"synthesized": true`; placeholder statements get the same flag on their
`speak` events. When a flipping jurist doesn't name who moved it, the engine's
guess is stamped `"influence_inferred": true`; a substituted flip reason is
stamped `"reason_inferred": true`. All flags are in
`contracts/events.schema.json` and render as ⚠ markers in the transcript
surfaces. Episode logs generated before 2026-07-06 predate the flags (the
schema keeps them optional, so old logs still validate).

## Tech stack

| Layer | Choice |
|---|---|
| Reasoning | `qwen3.7-plus` (9 jurists), `qwen3.7-max` (Foreperson, Clerk) via Qwen Cloud OpenAI-compatible API |
| Voices | Qwen3-TTS **Voice Design** — 12 custom voices created from text prompts (`qwen-voice-design` → `qwen3-tts-vd`) |
| Image gen | `wan2.6-t2i` (episode art), `qwen-image-2.0-pro` (show cover) |
| Sprites | [SpriteCook](https://spritecook.ai) character workflow (build-time assets) |
| Courtroom | Phaser 3 + Vite + TypeScript (deterministic event-log replay) |
| Case data | CourtListener REST v4 + [SCDB](http://scdb.wustl.edu/) + Oyez |
| Deploy | Alibaba Cloud SAS (pipeline) + OSS (podcast feed, courtroom app) |
| Pipeline | Python 3.11, `openai` SDK, ffmpeg |

## Quick start

```bash
git clone https://github.com/tmoody1973/split-decision && cd split-decision
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # add your keys (see table below)

# prove your models work (Day-1 gate)
.venv/bin/python scripts/verify_models.py

# ingest the case corpus (benchmark + memorization + pending sets)
.venv/bin/python scripts/ingest_cases.py

# run one full deliberation
.venv/bin/python scripts/deliberate.py --case data/cases/<case_id>.json
# -> episodes/<case_id>/events.jsonl + console summary of votes, flips, verdict
```

### Put any case in front of the panel

The corpus ships in the repo — pick any of the 170+ ingested cases in
`data/cases/` and convene the panel on it with the `deliberate.py` command
above. Nine jurists brief, vote privately, argue, and issue a verdict; the
full event log lands in `episodes/`. Fair warning: a deliberation is 150–200
reasoning-model calls and takes 45–90 minutes of wall clock for ~15 minutes
of actual argument — the replay player exists precisely to compress that into
performance speed.

## Environment variables

| Variable | Description | Required |
|---|---|---|
| `DASHSCOPE_API_KEY` | Qwen Cloud key (standard `sk-*`, **not** `sk-sp-*` Token Plan) | Yes |
| `DASHSCOPE_BASE_URL` | OpenAI-compatible endpoint (defaults to `dashscope-intl`) | No |
| `COURTLISTENER_TOKEN` | Free token from courtlistener.com — case ingestion | For ingestion |
| `SPRITECOOK_API_KEY` | Sprite generation (build-time only) | No |
| `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET` / `OSS_BUCKET` / `OSS_REGION` | Alibaba OSS publishing | For publishing |

Every API call's token usage is appended to `costs.jsonl` — the audit trail.

## Project structure

```
split-decision/
  contracts/        # THE spine: JSON Schemas for case records, events, cue sheets
  engine/           # deliberation chamber, clerk, personas, event log
  personas/         # 12 YAML personas: 9 jurists + foreperson + 2 anchors
                    #   (philosophy, flip trigger, voice_design_prompt, voice_id)
  scripts/          # verify_models, create_voices, ingest_cases, deliberate, ...
  data/             # case records, benchmark manifest, SCDB, landmark precedents
  assets/           # sprite sheets + manifest, voice previews, THEME.md
  episodes/         # per-case events.jsonl + audio & cue sheets (hero episodes committed)
  fixtures/         # hand-written smoke fixture for the courtroom renderer
  docs/             # PRD, hackathon requirements, design specs
```

**Blueprint-first:** every consumer builds against `contracts/*.schema.json`.
Events are emitted with `t: null` in sequence order; the podcast Producer assigns
final timestamps after TTS, and the courtroom player never re-derives timing.

## The cast

Nine jurist archetypes — never impersonations of real justices: the Textualist,
the Originalist, the Living Constitutionalist, the Pragmatist, the Precedent
Maximalist, the Federalism Hawk, the Civil Libertarian, the Process Formalist,
and the Minimalist. A Foreperson moderates without voting. Two journalist anchors
(a legal-affairs correspondent and a veteran court-watcher) cover the chamber as
a newsroom — the second agent society, exercising editorial curation over the
first one's record.

## Status

- [x] Model verification against live Qwen Cloud API
- [x] Contracts (case / events / cue-sheet schemas) + smoke fixture
- [x] 12 Voice Design voices created and locked
- [x] Case ingestion: contamination-guarded benchmark + two-tier memorization set + pending cases
- [x] Deliberation engine with anti-sycophancy machinery
- [x] Scoreboard (conditions A/B/C, paired analysis + memorization curve)
- [x] Podcast producer (clips → two-way script → TTS → ffmpeg → RSS)
- [x] Pixel courtroom + "The Record" transcript panel
- [x] SAS deployment ([split-decision.tarikmoody.com](https://split-decision.tarikmoody.com)) + OSS episode storage
- [x] 3-min demo video
- [ ] Workbench proof screenshot, architecture diagram, Devpost submission

## After the hackathon

The pending-case scoreboard keeps this alive: every time the real Court rules
on a predicted case, the season record updates. On the roadmap:

- **Listener-request docket** — pick a case from the term, the pipeline
  deliberates it overnight on Alibaba Cloud, and the episode appears in the
  podcast feed the next morning, like a request show for Supreme Court nerds.
- **Landmark re-litigation specials** — the panel re-argues a historical
  landmark (*Korematsu*, *Plessy*). Never benchmarked (the outcomes are in
  every model's training data), but the drama is different: not *what* the
  Court decided, but whether nine judicial philosophies hold up under
  embarrassment — does the Precedent Maximalist defend settled-but-shameful
  law? Civic education as a season finale.
- The engine itself is domain-independent — swap the corpus and personas for
  medical boards, code-review panels, or policy red teams.

## Data credits

Case data comes from three excellent free-law resources: [CourtListener](https://www.courtlistener.com)
by the nonprofit [Free Law Project](https://free.law) (become a member — this
project did), the [Supreme Court Database](http://scdb.wustl.edu/) at Washington
University, and [Oyez](https://www.oyez.org) for plain-English case summaries.

## License

[Apache-2.0](LICENSE)
