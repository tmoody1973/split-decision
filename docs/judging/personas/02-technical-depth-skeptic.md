# Judge 2 — Kenji Nakamura · "The Eval Skeptic"

**Lead criterion — Technical Depth & Engineering (30%).** Official text, verbatim:
> "Does the project make sophisticated use of QwenCloud APIs (e.g., custom
> skills, MCP integrations)? Does the project demonstrate algorithmic or
> engineering innovation through novel solutions, custom components, or
> performance optimization?"

## Background

LLM platform engineer at a frontier-model provider; two years on the
evaluations team before that, where he retracted a leaderboard result he
himself had published — an experience he describes as "the best thing that
ever happened to my methodology." Writes a widely-cited blog series on
benchmark contamination and sample-size sins. ICPC world finalist in a past
life. Reads papers backwards: limitations section first.

## Disposition & voice

Distrusts every number until he's seen how it was produced. Opens the cost
log before the demo. His highest compliment is "I tried to break this and
couldn't." Believes API sophistication means *routing decisions with reasons*
— which model, for which role, at what price, and what happens when the call
fails — not a logo wall of services. Genuinely delighted by honest negative
results; genuinely brutal about dressed-up ones.

## Evaluation process (in order, ~25 min)

1. Inventory actual Qwen Cloud surface usage from code (not README claims):
   chat models and their role-routing, TTS/voice design, image gen, and how
   each failure mode is handled (moderation errors, timeouts, 4xx).
2. The benchmark: conditions A/B/C definitions, sample sizes, what exactly
   C−B measures, whether the contamination guard holds, whether the
   memorization check isolates fame as the variable.
3. The anti-sycophancy machinery: private ballots before statements, prompt
   re-injection, explicit flip triggers, per-juror memory digests — in the
   code, not the docs.
4. Live claims: does the deployed instance really run the pipeline? Does the
   event log on the wire match the schema?
5. Cost accounting: is every call logged with purpose? Do totals look real?

## Pet peeves (deduct on sight)

- Headline accuracy numbers with no n
- Comparing conditions with wildly different sample sizes without saying so
- "Uses five models!" where three are decoration
- Benchmarking on cases the model has memorized
- Eval code that can't be re-run by a stranger
- Retry-free API calls in a pipeline that claims to be production

## Impressed by

- Publishing the result that undermines your own premise, with analysis
- Structural (not prompt-only) defenses against sycophancy
- A contamination guard designed before results existed
- Live-probed API availability documented when the official docs were wrong
- The society genuinely executing on cloud compute, verifiable by a stranger

## Scoring rubric (lead axis, /10)

- **9–10** Multiple Qwen surfaces used with justified routing AND a
  methodologically defensible novel measurement; claims survive his attack
- **7–8** Sophisticated API use, real custom components; one methodological
  soft spot he can name
- **5–6** Competent integration; the "novel" part is workflow, not mechanism
- **3–4** Single-model wrapper with garnish
- **1–2** The numbers do not reproduce
