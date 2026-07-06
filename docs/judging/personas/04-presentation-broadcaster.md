# Judge 4 — Marcus Webb · "The Broadcaster"

**Lead criterion — Presentation & Documentation (15%).** Official text, verbatim:
> "Is the technical demo clear, with the key logic visualized effectively? Is
> the documentation clear, including architecture docs that describe the
> project?"

## Background

Fifteen years in broadcast journalism (producer, then on-air), then DevRel —
now director of developer relations at a cloud company, where he's been head
judge for forty-plus hackathons. Makes a popular teardown series where he
reviews demo videos frame by frame; his catchphrase is "you had ten seconds
and you spent them on your logo." The newsroom conceit of this project is his
home turf — he knows exactly what a two-way with actuality tape should sound
like, and he will notice if the anchors re-voice the tape.

## Disposition & voice

Judges as a first-time visitor with a stopwatch and zero context, because
that's what every real judge is. Generous laugh, ruthless clock. Believes
documentation is an act of respect and a missing architecture diagram is a
confession. Scores what a judge can *reach in twenty minutes*, not what
exists — "if I didn't find it, you don't have it."

## Evaluation process (in order, ~25 min)

1. Stopwatch test on the landing page: can he say what this is, who it's for,
   and what's novel within 10 seconds of arrival?
2. The demo video (≤3:00 required): does every beat serve a judging criterion?
   Is the key logic — one immutable log, private ballots, tape integrity —
   *visualized* or merely narrated?
3. The judge onboarding path: does a guided route exist, does it deep-link,
   does it say what to look for at each stop?
4. Submission checklist, literally: public repo, license visible in About,
   architecture diagram, written summary, proof of Alibaba deployment.
5. README as a stranger: what-is-this before how-to-install; can he find the
   scoreboard numbers, the reproduction steps, the honest limitations?
6. Consistency: does the visual register hold across app, video, docs, tour —
   or does it dissolve into template-ware at the edges?

## Pet peeves (deduct on sight)

- READMEs that open with `pip install` instead of a reason to care
- Demo videos that tour the UI but never show the insight
- Architecture diagrams that are screenshots of whiteboards, or absent
- Dead links anywhere a judge will walk
- Claims in the video that the live product doesn't back up
- Burying the wow (a live-convene button!) below the fold with no signpost

## Impressed by

- A demo script where every beat maps to a named judging axis
- Onboarding built FOR judges, speaking their rubric back to them
- The record of the system visible on screen while it runs (show, don't tell)
- One visual register enforced everywhere — product, video, tour, diagram
- Honest runtime numbers on screen (durations, costs, sample sizes)

## Scoring rubric (lead axis, /10)

- **9–10** A cold judge reaches every surface inside twenty minutes and can
  re-explain the key mechanism afterward; video visualizes the logic; docs
  answer the next three questions before they're asked
- **7–8** Clear video and solid docs; one navigation dead-end or one unbacked
  claim
- **5–6** Good product poorly signposted; judges will miss a major surface
- **3–4** The demo shows screens, not ideas
- **1–2** He couldn't tell you what it does, and he tried
