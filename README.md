# ⚖️ Split Decision

**An agent society deliberates real Supreme Court cases.** Nine AI jurists with
distinct judicial philosophies argue, persuade, and flip votes — while an AI
newsroom turns every deliberation into a two-journalist podcast and a pixel-art
courtroom replay. The panel's predictions are scored against the real Court's
rulings, including cases the Court hasn't decided yet.

Built for the **Qwen Cloud Global AI Hackathon — Track 3: Agent Society**.

> 🚧 Active build (July 2026). Full README with architecture diagram, scoreboard
> results, and episode links lands at submission. The engineering blueprint is
> in [CLAUDE.md](CLAUDE.md); the product spec is in [docs/PRD.md](docs/PRD.md).

## The core question

Does structured multi-agent deliberation beat solo reasoning on hard judgment
tasks with verifiable ground truth? We measure it three ways on
contamination-guarded SCOTUS cases (decided after all model training cutoffs):

- **A. Solo** — one model, one prediction
- **B. Silent jury** — nine philosophically distinct jurists vote independently
- **C. Society** — full structured deliberation: private votes, statements,
  paired debate, revotes

**C − B is the value of deliberation itself.** A memorization-check arm
(famous landmarks vs. ordinary historical cases) quantifies training-data
contamination and shows why the benchmark only counts post-cutoff cases.

## Tape integrity rule

Every podcast clip is verbatim from `events.jsonl` — the same immutable event
log that feeds the scoreboard, the courtroom renderer, and the transcript
panel. The journalists characterize; they never rewrite the record.

## License

[Apache-2.0](LICENSE)
