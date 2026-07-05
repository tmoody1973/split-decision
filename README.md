# ⚖️ Split Decision

> Nine AI jurists with distinct judicial philosophies deliberate real Supreme Court
> cases — arguing, persuading, and flipping votes — while an AI newsroom turns every
> deliberation into a podcast and a pixel-art courtroom replay. The panel's
> predictions are scored against the real Court, including cases it hasn't decided yet.

Built for the **Qwen Cloud Global AI Hackathon — Track 3: Agent Society** ·
Submission July 8, 2026 · Solo build by [Tarik Moody](https://github.com/tmoody1973)

> 🚧 **Active build (Day 1–2 of 5).** The deliberation engine and data layer are
> live; scoreboard results, published episodes, the courtroom app, and the
> architecture diagram land here at submission. Blueprint: [CLAUDE.md](CLAUDE.md) ·
> Product spec: [docs/PRD.md](docs/PRD.md)

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

## Results (first full run, July 5, 2026)

| Condition | Post-cutoff accuracy | Famous landmarks | Ordinary historical |
|---|---|---|---|
| A — solo `qwen3.7-max` | **83.0%** (n=94) | 95.8% | 96.0% |
| B — silent jury of 9 | 77.4% (n=93) | 95.8% | 100% |
| C — full deliberation | **66.7%** (n=24) | — | — |

Three measured findings, reproducible via `scripts/run_benchmark.py`:

1. **Contamination is ~15 points and reaches obscure cases.** The model scores
   96–100% on *anything* pre-cutoff — even cases no law student has heard of —
   vs 77–83% on post-cutoff cases. Benchmarks on historical rulings are
   measuring memory, not judgment.
2. **More agents, worse predictions — monotonically.** A > B > C. Nine
   philosophically committed jurists vote their philosophies; the real Court
   is more unanimous than a panel of ideologues (jury split-distance 2.0 vs
   solo 0.73). Deliberation amplified rather than corrected: 85 argued vote
   changes across 24 cases, and accuracy fell another 10 points.
3. **Steerability follows philosophy.** Flip counts per juror: Minimalist 21,
   Pragmatist 14, Precedent Maximalist 13 … Originalist 1, Textualist 1. The
   archetypes anchored to fixed sources (text, history) are nearly immovable;
   the ones anchored to case-by-case judgment sway constantly.

Deliberation makes worse predictions and much better arguments — which is the
honest trade this project set out to measure. (One of 25 deliberation cases
failed on a content-moderation block and is excluded; per-case predictions
live in `scoreboard/predictions/`.)

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
  episodes/         # per-case events.jsonl (+ audio & cue sheets, from Day 3)
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
- [ ] Scoreboard (conditions A/B/C + memorization curve)
- [ ] Podcast producer (clips → two-way script → TTS → ffmpeg → RSS)
- [ ] Pixel courtroom + "The Record" transcript panel
- [ ] SAS + OSS deployment, proof screenshot
- [ ] 3-min demo video, architecture diagram, Devpost submission

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
