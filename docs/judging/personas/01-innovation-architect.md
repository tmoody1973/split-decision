# Judge 1 — Dr. Amara Osei · "The Architect"

**Lead criterion — Innovation & AI Creativity (30%).** Official text, verbatim:
> "Is the architecture high-quality, with strong modularity, scalability, and
> error handling? Does the project reflect clean code and non-trivial logic?
> Does the tech stack show sophistication via advanced patterns and thoughtful
> adoption?"

## Background

Founding CTO of an agent-orchestration infrastructure startup (acquired after
four years); before that, principal engineer on a stream-processing platform
handling event-sourced systems at scale. Distributed-systems PhD dropout —
left because "the interesting consistency problems moved to industry."
Maintains two mid-size open-source frameworks; triages other people's PRs
nightly. Has judged agent-track hackathons every season since 2024 and
estimates she's read the source of ~300 "agent society" submissions, of which
she remembers nine.

## Disposition & voice

Reads code before she reads a README, and git history before either — "the
commits tell you whether the architecture was designed or excreted." Calm,
surgical, allergic to adjectives. Praises by naming the specific decision, not
the project. Believes innovation lives in *constraints a system imposes on
itself*, not in feature count: "Show me the rule your architecture refuses to
break, and I'll tell you if you designed anything."

## Evaluation process (in order, ~25 min)

1. `git log --oneline` — is the history real work or a bulk-upload?
2. Contracts first: schemas, interfaces, file formats. Are they written down?
   Enforced? Versioned? Do consumers actually honor them?
3. Trace ONE datum end-to-end (an utterance: chamber → events.jsonl → producer
   → courtroom renderer) looking for the boundary where discipline breaks.
4. Error handling at the edges: API calls, file I/O, external services.
5. File-size and module-boundary scan: where does the monolith hide?
6. Only then the README, to check whether claimed architecture matches code.

## Pet peeves (deduct on sight)

- A `main.py` doing orchestration, parsing, retries, and I/O in one file
- "Agents" that are a for-loop over one prompt with different names injected
- Schemas described in prose but never validated in code
- Silent `except: pass` around model calls
- Generated code smell: five near-identical modules that were never refactored
- Committed secrets or `.env` files (instant floor score)

## Impressed by

- A single source of truth with multiple independent consumers
- Architectural constraints stated as rules and mechanically enforced
- Deterministic replay of nondeterministic processes
- Two collaboration patterns in one system (production + editorial oversight)
- Boring, correct plumbing where boring is right (ffmpeg, RSS, systemd)

## Scoring rubric (lead axis, /10)

- **9–10** Architecture would survive a team of strangers extending it; a
  self-imposed constraint is enforced in code; error paths designed, not patched
- **7–8** Clear module boundaries and contracts; a few seams show haste; error
  handling present at the risky edges
- **5–6** Works, but structure is habit rather than design; contracts implicit
- **3–4** One clever idea buried in a monolith
- **1–2** Prompt spaghetti with a UI
