# PRD — SPLIT DECISION

**Version:** 1.0 · July 4, 2026 · Owner: Tarik Moody
**Companion doc:** CLAUDE.md (engineering blueprint — the *how*; this is the *what/why*)
**Target:** Qwen Cloud Global AI Hackathon, Track 3: Agent Society · Ship by July 8, 2026

---

## 1. One-liner

Nine AI jurists with distinct judicial philosophies deliberate real Supreme Court
cases — arguing, persuading, and flipping votes — while an AI newsroom turns every
deliberation into a two-journalist podcast and a watchable pixel-courtroom replay.
The panel's predictions are scored against the real Court's actual rulings, including
cases the Court hasn't decided yet.

## 2. Problem & why it matters (mapped to the 25% "Problem Value & Impact" rubric)

1. **Authentic technical pain point (primary):** Teams shipping multi-agent systems
   cannot answer the most expensive question in the pattern: *does deliberation
   actually improve decisions, or does it just multiply inference cost?* A known
   failure mode — agents collapsing into sycophantic consensus — is undetectable in
   most stacks. Split Decision ships (a) a benchmark methodology: solo model vs.
   silent majority vote vs. full deliberation, scored against verifiable ground
   truth; and (b) a tested anti-sycophancy reference implementation (private
   scratchpad votes, persona re-anchoring, forced disagreement pairing). A developer
   leaves the repo knowing whether, when, and why paying 10x for a panel beats one
   model call. SCOTUS outcomes are the ideal test corpus: hard, public, formally
   adjudicated judgment calls with free authoritative ground truth.
2. **Business relevance (secondary):** Litigation-outcome prediction is an existing
   commercial category, and the deliberation-ensemble pattern generalizes to any
   high-stakes judgment an organization wants structured second opinions on —
   moderation appeals, grant triage, decision review. We demonstrate the pattern
   where ground truth costs nothing.
3. **Scalability & open-source potential:** The engine is domain-independent — swap
   corpus and personas for medical boards, code-review panels, policy red teams.
   The event-sourced architecture (one immutable log, four consumers: scoreboard,
   podcast, courtroom, transcript) is a reusable observability pattern for making
   any agent system legible. The pending-case scoreboard makes this a living public
   benchmark that updates itself every time the real Court rules.
4. **Public legibility (the distribution layer):** rendering deliberation as audio
   journalism and animation turns machine disagreement into something citizens can
   hear, watch, and evaluate — civic education about courts and AI. This is how the
   research travels; it is not the product's core claim.

## 3. Audience

| Who | Job to be done |
|---|---|
| Hackathon judges | Assess technical depth (deliberation architecture, anti-sycophancy machinery, benchmark honesty) and innovation in <10 min |
| AI researchers/builders | Reusable pattern: measurable deliberation protocol + event-sourced multi-consumer architecture |
| Court-curious public | An entertaining, trustworthy way to understand pending Supreme Court cases |

## 4. Product pillars (in priority order — cut from the bottom, never the top)

1. **The Chamber** — 9 archetype jurists + foreperson; structured rounds with private
   votes, open statements, paired debate; genuine reasoned vote changes
2. **The Scoreboard** — solo model vs. silent-vote jury vs. deliberating society on
   20 contamination-guarded cases; deliberation's lift (or honest lack of it) is the
   headline number
3. **The Show** — two AI journalist anchors (lead correspondent + court-watcher
   analyst) covering the chamber; verbatim tape only; published podcast feed (RSS)
4. **The Replay** — pixel courtroom (SpriteCook sprites, Phaser) + "The Record" live
   transcript panel with click-to-seek; vote board flips on camera
5. **The Bet** — 2–3 pending cases predicted on the record

## 5. What Split Decision is NOT

- Not legal advice, not outcome-betting infrastructure, not a claim about how the
  real Court reasons
- Not an impersonation of any real justice — all personas are judicial-philosophy
  archetypes
- Not a chatbot — there is no chat UI anywhere in the product

## 6. Success criteria

**Must ship (definition of done):**
- [ ] 1 hero episode (pending case): podcast MP3 + courtroom replay + Record panel,
      end-to-end on Alibaba Cloud (Function Compute + OSS), publicly reachable
- [ ] Scoreboard across ≥12 benchmark cases with all three conditions, published
      honestly in README
- [ ] ≥1 genuine, reasoned on-tape vote flip in the hero episode
- [ ] Public Apache-2.0 repo, architecture diagram, proof-of-deployment recording,
      3-min video, Devpost submission in Track 3

**Should ship:** 20-case benchmark · 3+ episodes in the feed · click-to-seek demo
moment in video · blog post (Blog Post Award)

**Quality bars:**
- A first-time listener can follow the hero episode with zero setup (anchors carry it)
- All 12 voices distinguishable blind (the Day-1 listen test)
- Scoreboard reproducible from the repo with one command + API keys

## 7. Experience walkthrough (hero flow)

1. Visitor opens the episode page → pixel courtroom left, The Record right
2. Presses play: anchors' cold open over a studio card (or news-desk scene if built),
   then wipe to chamber as the first tape block plays
3. Jurists walk to the lectern and argue; transcript scrolls in sync; round-2 private
   votes post to the board
4. Round 3: the Pragmatist flips — sprite flash, board tile flips with a chime, The
   Record prints the highlighted system line, the analyst anchor calls it on tape
5. Verdict: 6–3 reverse. Card: *"The real Supreme Court has not yet decided this case.
   Prediction filed July 8, 2026."*
6. Below the fold: season scoreboard — society vs. solo vs. silent jury

## 8. Differentiation (laziest-competitor test)

The default Track 3 entry is agents-as-coworkers doing office tasks. Against that:
verifiable ground truth (predictions scored against reality), a second agent society
(the newsroom) with an enforced integrity boundary between record and coverage,
an event-sourced architecture where four products (scoreboard, podcast, courtroom,
transcript) consume one immutable log, and a falsifiable public bet. None of these
survive being bolted on at the end — they are the architecture.

## 9. Constraints & risks (full log in CLAUDE.md)

- $40 Qwen Cloud coupon → jurors on qwen-plus, costs logged per call, hero assets cached
- Contamination: benchmark restricted to post-June-2025 decisions + pending cases;
  stated openly in README and video
- Consensus collapse risk: private-vote/public-statement separation; a null result is
  reported as a finding, not hidden
- 5-day build: pillar order above is the cut order, bottom-up

## 10. Post-hackathon signal (one paragraph, because judges ask)

The pending-case scoreboard keeps the artifact alive after judging — every real
Supreme Court ruling this term updates the season record. Format extends to any
deliberative body with recorded outcomes (circuit courts, arbitration, legislative
votes), and the event-sourced deliberation engine is a reusable open-source pattern
independent of the legal domain.
