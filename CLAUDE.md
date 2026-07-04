# CLAUDE.md — SPLIT DECISION

> An agent society deliberates real Supreme Court cases — nine AI jurists with
> distinct judicial philosophies argue, persuade, flip votes, and predict outcomes.
> Every deliberation is autonomously produced into a multi-voice podcast episode
> AND rendered as a pixel-art animated courtroom you can watch.
>
> **Hackathon:** Qwen Cloud Global AI Hackathon — Track 3: Agent Society
> **Submission deadline:** July 8, 2026 (build to the 8th; official cutoff July 9, 2pm PDT)
> **Judging:** Technical Depth 30% · Innovation 30% · Problem Value 25% · Presentation 15%

---

## 0. Prime Directives (read before every session)

1. **Blueprint-first (bumwad).** No phase begins until its contract (schema, interface,
   file format) is written and committed. Contracts live in `/contracts`.
2. **The event log is the spine.** Deliberation engine, scoreboard, podcast producer,
   and pixel courtroom are all consumers of the same `events.jsonl`. Never let a
   consumer require data the event schema doesn't carry — extend the schema first.
3. **Cache the wow.** Nothing live runs during the demo video. Every hero asset
   (episode audio, courtroom replay, scoreboard) is precomputed and committed to
   `/episodes/`.
4. **Contamination guard.** Benchmark cases MUST be decided after 2025-06-01 or be
   obscure per-curiam decisions. Pending (undecided) cases are the headline.
   Never benchmark on famous cases — Qwen has memorized them.
5. **$40 token budget.** Log every API call's token usage to `costs.jsonl`.
   Jurors run on `qwen-plus`. Only the Foreperson and Clerk run `qwen-max`.
6. **Everything to OSS immediately.** Qwen-Image URLs expire in 24h. Any generated
   asset is downloaded and pushed to Alibaba OSS in the same function that created it.
7. **Open source hygiene.** Apache-2.0 LICENSE at repo root, visible in About.
   No secrets in code, ever. `.env.example` documents every variable.
8. **Personas are archetypes, never real justices.** No real names, no impersonation.

---

## 1. System Architecture

```
                        ┌─────────────────────────────────────────┐
                        │        ALIBABA CLOUD (Singapore)        │
                        │                                         │
  CourtListener API ───▶│  ┌──────────┐    ┌──────────────────┐   │
  Oyez API ────────────▶│  │  CLERK   │───▶│   DELIBERATION   │   │
  SCDB CSV (local) ────▶│  │  agent   │    │     CHAMBER      │   │
                        │  │ qwen-max │    │  9 × qwen-plus   │   │
                        │  └──────────┘    │  + Foreperson    │   │
                        │   bench memo     │    (qwen-max)    │   │
                        │   + precedents   └────────┬─────────┘   │
                        │                           │             │
                        │                    events.jsonl         │
                        │                           │             │
                        │        ┌──────────────────┼───────────┐ │
                        │        ▼                  ▼           ▼ │
                        │  ┌───────────┐    ┌────────────┐ ┌────────────┐
                        │  │ SCOREBOARD│    │  PRODUCER  │ │ COURTROOM  │
                        │  │ benchmark │    │   agent    │ │  renderer  │
                        │  │  metrics  │    │ qwen-plus  │ │ (Phaser 3, │
                        │  └───────────┘    └─────┬──────┘ │  browser)  │
                        │                         │        └────────────┘
                        │              ┌──────────┼──────────┐            
                        │              ▼          ▼          ▼            
                        │        Qwen3-TTS   Qwen-Image   cue_sheet.json  
                        │        (voices)    (ep. art)                    
                        │              │          │                       
                        │              ▼          ▼                       
                        │        ffmpeg mix → MP3 + RSS → OSS bucket      
                        └─────────────────────────────────────────┘
                                       │
                          Function Compute (pipeline runner)
                          OSS static hosting (podcast feed + courtroom app)
```

**Deploy targets (proof-of-deployment recording covers these):**
- **Function Compute** — the pipeline orchestrator (`run_episode.py` as an HTTP-triggered function)
- **OSS** — static hosting: podcast MP3s, RSS feed, episode art, and the built courtroom web app
- Region: **Singapore (ap-southeast-1)** for Model Studio. Beijing-region keys DO NOT work here.

---

## 2. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| Language (pipeline) | Python 3.11 | dashscope SDK for Model Studio |
| Reasoning models | `qwen-plus` (9 jurors), `qwen-max` (Foreperson, Clerk) | Singapore endpoint |
| TTS | Qwen3-TTS via Model Studio — **Voice Design** for 10 distinct voices | 10 free voice creations; batch (non-realtime) synthesis |
| Image gen | `qwen-image-plus` (episode art), `qwen-image-2.0-pro` (show cover — best text rendering) | download → OSS immediately, URLs die in 24h |
| Sprites | **SpriteCook via MCP** (`npx spritecook-mcp setup`) | generated at BUILD TIME, committed as static assets |
| Courtroom renderer | Phaser 3 + Vite, TypeScript | deterministic replay of events.jsonl + cue sheet |
| Audio assembly | ffmpeg (concat + music bed ducking) | runs inside Function Compute layer or locally |
| Case data | CourtListener REST v4 + SCDB CSV + Oyez | free, token auth for CourtListener |
| Storage | Alibaba OSS | episodes, art, RSS, courtroom app |
| Vector store (precedent RAG) | Simple: JSON + local embedding is fine at this scale. Stretch: DashVector | 20–30 cases → don't over-engineer |

**Endpoint boilerplate (Singapore):**
```python
import dashscope
dashscope.base_http_api_url = "https://{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com/api/v1"
# API key: env var DASHSCOPE_API_KEY (Singapore-region key ONLY)
```

---

## 3. Data Layer

### 3.1 Sources

| Source | What we take | Access |
|---|---|---|
| **CourtListener REST v4** `/api/rest/v4/clusters/?docket__court=scotus` | case name, dates, syllabus, opinion text (`html_with_citations`), `scdb_id` | free token — `Authorization: Token <key>` |
| **CourtListener search API** `/api/rest/v4/search/?court=scotus&q=...` | discovery of recent + pending-adjacent cases | same token |
| **SCDB CSV** (download once, commit to `/data/scdb/`) | coded ground truth: `caseDisposition`, `decisionDirection`, `majVotes`, `minVotes`, `issueArea` | free CSV, no auth |
| **Oyez** `api.oyez.org/cases/{term}/{docket}` | plain-English facts + question presented (great for scripts) | free, no auth |

### 3.2 Case selection rules (contamination guard — CRITICAL)

- **Benchmark set (n=20):** cases ARGUED and DECIDED after 2025-06-01, joined to SCDB
  (or hand-coded outcome if SCDB lags). These post-date model training.
- **Headline set (n=2–3):** cases argued this term but NOT YET DECIDED as of submission.
  The society's prediction goes on the record. Uncontaminatable by definition.
- **NEVER** include landmark/famous cases in the benchmark. If a case name would be
  recognized by a first-year law student, exclude it.
- Store the frozen case list in `/data/benchmark_manifest.json` with selection rationale.

### 3.3 Case record format (`contracts/case.schema.json`)

```json
{
  "case_id": "cl-cluster-12345",
  "name": "Smith v. Jones",
  "docket": "24-123",
  "date_argued": "2026-01-12",
  "date_decided": "2026-05-30",        // null for pending cases
  "question_presented": "...",          // from Oyez or syllabus
  "facts_summary": "...",               // Clerk-generated, ≤400 words
  "lower_court_ruling": "affirmed|reversed|...",
  "opinion_excerpt_urls": ["..."],
  "ground_truth": {                     // null for pending
    "disposition": "reversed",
    "vote_split": "7-2",
    "scdb_id": "2025-031"
  },
  "status": "decided|pending"
}
```

---

## 4. THE CONTRACT: Event Schema (`contracts/events.schema.json`)

Every deliberation emits `episodes/{case_id}/events.jsonl` — one JSON object per line.
All timestamps `t` are milliseconds from episode start, computed AFTER TTS (durations known).

```jsonc
// type: "session_start"
{"t": 0, "type": "session_start", "case_id": "cl-12345", "round": 0}

// type: "speak" — one utterance. THE core event.
{"t": 42300, "type": "speak", "agent": "textualist", "round": 2,
 "text": "The statute says 'shall,' not 'may.' That ends it for me.",
 "audio_file": "utt_017.mp3", "dur_ms": 6400,
 "stance": "reverse", "confidence": 0.85}

// type: "vote" — private scratchpad vote at round boundary (drives scoreboard)
{"t": 48700, "type": "vote", "agent": "pragmatist", "round": 2,
 "position": "affirm", "confidence": 0.6, "public": false}

// type: "vote_change" — a flip. THE wow event. Courtroom flashes, board flips.
{"t": 91200, "type": "vote_change", "agent": "pragmatist", "round": 3,
 "from": "affirm", "to": "reverse",
 "influenced_by": ["textualist", "federalism_hawk"],
 "reason_text": "...", "audio_file": "utt_031.mp3", "dur_ms": 5100}

// type: "foreperson" — moderation acts: pairing disagreements, calling votes
{"t": 95000, "type": "foreperson", "action": "pair_debate",
 "agents": ["living_constitutionalist", "textualist"],
 "text": "...", "audio_file": "utt_032.mp3", "dur_ms": 4200}

// type: "move" — renderer hint (bench|lectern|huddle). Producer inserts these.
{"t": 42300, "type": "move", "agent": "textualist", "to": "lectern"}

// type: "verdict"
{"t": 480000, "type": "verdict", "position": "reverse", "vote_split": "6-3",
 "dissenters": ["pragmatist_2", "minimalist", "process_formalist"]}

// type: "reveal" — decided cases only
{"t": 495000, "type": "reveal", "actual": "reverse", "actual_split": "7-2",
 "match": true}
```

**Rules:**
- `agent` values come ONLY from the persona registry (§6). Renderer hard-fails on unknown agents.
- `audio_file` paths are relative to the episode dir.
- The Producer, not the deliberation engine, assigns final `t` values (it knows TTS durations).
  The engine emits events with `t: null` and sequence order; Producer fills timestamps.

```jsonc
// type: "studio" — anchor segments (podcast layer only; NOT part of deliberation).
// Lives in a separate stream: episodes/{case_id}/studio_events.jsonl
{"t": 0, "type": "studio", "agent": "anchor_lead",
 "text": "...that's the Textualist, about ninety seconds before the whole panel flipped.",
 "audio_file": "studio_003.mp3", "dur_ms": 5800}

// type: "tape_ref" — studio stream pointer into deliberation events (clip playback)
{"t": 5800, "type": "tape_ref", "clip_id": "c02",
 "event_span": [17, 24], "dur_ms": 48000}
```

**Stream separation rule:** `events.jsonl` = the deliberation record, immutable once
generated. `studio_events.jsonl` = the journalists' show, which references but never
contains deliberation content. Scoreboard reads only the former. Podcast assembly
interleaves both via the cue sheet.

### 4.1 Cue sheet (`episodes/{case_id}/cue_sheet.json`)
Derived view for the renderer + video export: ordered `{t, event_index, audio_file, dur_ms}`,
now spanning both streams (studio segments + tape blocks).
The Phaser player consumes cue sheet + events; it never re-derives timing.

---

## 5. Sprite Pipeline (SpriteCook MCP)

### 5.1 Setup (once, Day 1)
```bash
npx spritecook-mcp setup     # auto-configures Claude Code MCP + agent skills
# API key from app.spritecook.ai/api-keys → env SPRITECOOK_API_KEY
```

### 5.2 Workflow rules
- Create **one SpriteCook theme/style guide first** and reference it for every asset
  (style consistency via reference IDs — this is SpriteCook's whole advantage).
  Theme prompt lives in `/assets/sprites/THEME.md`. Suggested register:
  *"16-bit courtroom drama. Warm wood tones, deep judicial navy and burgundy robes,
  soft key light from tall windows. Dignified but slightly caricatured proportions,
  readable at 96px. Clean grid, no anti-aliasing."*
- Per jurist: **idle** (2–4 frame preset) and **walk** (preset) animations. Talking =
  code-side bubble + subtle bob; do NOT generate talk frames (scope trap).
- Also generate: foreperson/host character, courtroom background (bench, gallery,
  lectern, vote board as separate layers), gavel prop, vote-board tiles.
- Export transparent PNG sprite sheets → commit to `/assets/sprites/` with
  `/assets/sprites/manifest.json`:

```json
{
  "textualist": {
    "sheet": "textualist.png", "frame_w": 96, "frame_h": 96,
    "anims": {"idle": [0,1,2,1], "walk": [3,4,5,6]},
    "palette_accent": "#7a1f2b"
  }
}
```

- **License note:** confirm SpriteCook ToS grants ownership/redistribution of generated
  assets before committing to the public repo (check on Day 1; fallback = Kenney CC0 pack,
  manifest format unchanged).
- Sprites are **build-time assets**. Runtime image generation (episode art) stays on
  Qwen-Image — sponsor tech in the live pipeline, SpriteCook in the toolchain.

---

## 6. Persona Registry (`personas/*.yaml`)

Nine jurists + Foreperson + Host. Archetypes, not people. Each YAML:

```yaml
id: textualist
display_name: "The Textualist"
voice_design_prompt: >
  Older male voice, gravelly, deliberate, low pitch, slight Southern cadence,
  speaks in short declarative sentences, dry wit.
voice_id: null            # filled after Voice Design call, committed
system_prompt: |
  You are a jurist on a nine-member deliberative panel. Your judicial philosophy:
  the text of the statute or Constitution controls. Legislative history is noise.
  Consequences are the legislature's problem, not yours.
  Interpretive hierarchy: plain meaning > structure > canons > (never) purpose-talk.
  Style: terse, quotes the operative words verbatim, impatient with policy arguments.
  You change your vote ONLY when shown text or structure you had not accounted for.
  You are in round {round}. Prior rounds: {memory_digest}.
  Your current private position: {position} (confidence {confidence}).
bias_axes: {textualism: 0.95, precedent_weight: 0.5, pragmatism: 0.1, federalism: 0.6}
```

**The nine:**
1. `textualist` — text controls, full stop
2. `originalist` — original public meaning; history-and-tradition tests
3. `living_constitutionalist` — evolving standards, purposive reading
4. `pragmatist` — consequences and workability first
5. `precedent_maximalist` — stare decisis über alles; reliance interests
6. `federalism_hawk` — state sovereignty, anti-commandeering instincts
7. `civil_libertarian` — individual rights presumption against the state
8. `process_formalist` — jurisdiction, standing, procedure before merits
9. `minimalist` — decide narrowly, avoid the big question if possible

Plus: `foreperson` (qwen-max; moderates, never votes) and **two journalist anchors**
who host the podcast as a newsroom covering the chamber:
- `anchor_lead` — legal-affairs correspondent. Precise, warm, carries the facts and
  procedural stakes. Public-radio two-way register.
- `anchor_analyst` — veteran court-watcher. Wry, skeptical, tracks the personalities
  and coalition dynamics ("watch the pragmatist here — she's been drifting since
  round two"). Brings the color, calls the flips before they happen.
Their contrast is structural: lead explains the LAW, analyst reads the ROOM. Write
their two-way chemistry into both system prompts (they reference each other by role).

**Voice Design (Day 1):** one script `scripts/create_voices.py` calls Voice Design
per persona, saves preview MP3s to `/assets/voice_previews/`, writes `voice_id` back
to YAML. LISTEN to all twelve before proceeding. Distinctiveness is the product.
Budget: 12 voices = 10 free creations + 2 × $0.20. Regenerations $0.20 each; cap at 5.
Design the two anchors FIRST — they carry the most airtime per episode.

---

## 7. Deliberation Protocol (state machine)

```
INIT → BRIEFING → [ROUND]* → VERDICT → (REVEAL if decided)

ROUND (max 5):
  1. PRIVATE_VOTE     each juror: scratchpad position + confidence (not shown to others)
  2. STATEMENTS       jurors speak in Foreperson-chosen order; each sees transcript so far
  3. PAIR_DEBATE      Foreperson picks the 1-2 sharpest disagreements → direct exchanges
                      (2 turns each side, max)
  4. REVOTE           private votes again → diff vs step 1 emits vote_change events
  5. CHECK            ≥7-2 supermajority OR round == 5 → VERDICT; else next ROUND
```

**Anti-sycophancy machinery (this is the Technical Depth story — document it in README):**
- Private scratchpad votes BEFORE public statements each round (positions form
  independently, then deliberation acts on them — measurable persuasion, not mimicry)
- Persona system prompt re-injected EVERY round (drift resistance)
- Each persona has an explicit "you change your vote only when..." trigger condition
- Foreperson is structurally barred from stating a position; prompt-audited
- Memory digest: each juror carries a ≤300-token rolling summary of prior rounds
  written from ITS OWN perspective (its `memory_digest`), not a shared neutral summary

**Token budget per case:** 9 jurors × 5 rounds × ~900 tokens I/O ≈ 40–50K + Foreperson/Clerk
≈ 70K total. 25 cases ≈ 1.75M tokens on mostly qwen-plus → comfortably inside $40.
Track in `costs.jsonl`; alert (print red) at $25 cumulative.

---

## 8. Scoreboard / Benchmark (`scoreboard/`)

Three conditions per benchmark case, all on identical case records:
- **A. Solo:** single `qwen-max` predicts disposition + split (1 call)
- **B. Independent jury:** 9 personas vote once, no communication; majority wins
- **C. Society:** full deliberation protocol
Metrics: disposition accuracy, split-distance (|predicted majVotes − actual|),
flip count, rounds-to-consensus. Output `scoreboard/results.json` + a rendered table
in README. **C − B = the value of deliberation itself** — the headline number.
If C ≤ B, report it honestly as a finding and analyze which cases deliberation helped/hurt.
An honest negative result with analysis scores better on Technical Depth than a fudged win.

---

## 9. Podcast Production Pipeline (Producer agent)

**Format: a two-journalist newsroom covering the deliberation chamber.** The anchors
frame, play "tape" (clips from the deliberation), and react — classic two-way +
actuality structure.

**TAPE INTEGRITY RULE (non-negotiable, state it in README):** every deliberation clip
is verbatim from `events.jsonl` — the same log that feeds the scoreboard and courtroom.
Anchors may characterize and analyze; they may NEVER paraphrase, re-voice, or alter a
juror's words or votes. The script pass selects clip spans by event index, it does not
rewrite them. Podcast, scoreboard, and courtroom share one source of truth.

Per episode (`scripts/run_episode.py --case cl-12345`):
1. **Newsroom pass** (qwen-plus, two calls):
   a. *Clip selection* — given the transcript, select 6–10 tape blocks by event index:
      the sharpest exchange (cold open), each vote_change and its trigger, the verdict.
      Output: `clip_manifest.json` (spans of event indices, no text rewriting).
   b. *Two-way script* — anchors' dialogue wrapping the clips. Structure: cold open
      (10s of hot tape, then "...that's the Textualist, about ninety seconds before
      the whole panel flipped — I'm {anchor_lead}...") → facts two-way (from Oyez
      plain-English; lead explains, analyst raises the stakes) → tape blocks with
      anchor setups and reactions → verdict tape → reveal segment for decided cases
      or "prediction on the record" for pending → season scoreboard check-in
      ("the panel is now 14-for-17 this term") → outro. Target 12–18 min.
      Anchor lines carry `speaker: anchor_lead|anchor_analyst` in the script JSON.
2. **TTS pass:** every utterance → Qwen3-TTS batch with the speaker's `voice_id` →
   `utt_NNN.mp3`. Record durations.
3. **Timestamp pass:** fill event `t` values; write `cue_sheet.json`.
4. **Assembly:** ffmpeg concat with 300ms gaps, music bed under host segments
   (bed ducked −14dB under speech; source a CC0 bed, commit license note).
5. **Art pass:** Producer writes a scene-descriptive art prompt (style-locked:
   *"hand-drawn courtroom sketch, warm pastel, loose ink lines"*) → `qwen-image-plus`
   → download → OSS. Show cover uses `qwen-image-2.0-pro` (renders "SPLIT DECISION" text).
   **Prompt rule: describe the SCENE, never the underlying crime/violence —
   avoids DataInspectionFailed moderation errors.**
6. **Publish:** upload MP3 + art to OSS; regenerate `feed.xml` (RSS 2.0 + podcast
   namespace); episode page links the courtroom replay.

---

## 10. Pixel Courtroom Renderer (`courtroom/`, Vite + Phaser 3 + TS)

Deterministic player. No game logic — a timeline VCR.

```
courtroom/
  src/
    main.ts            // boot, load manifest + episode
    TimelinePlayer.ts  // THE core class — see below
    Stage.ts           // bench, lectern, gallery, vote board layout
    JuristSprite.ts    // idle/walk anims, bob-while-speaking, bubble anchor
    VoteBoard.ts       // 9 tiles, flip animation + chime on vote_change
    Bubble.ts          // speech bubble w/ typewriter text
  public/
    assets/sprites/    // symlink or copy of /assets/sprites
    episodes/          // events.jsonl + cue_sheet.json + utt mp3s
```

**TimelinePlayer contract:**
- `load(episodeDir)` → fetch events + cue sheet + preload audio
- `play() / pause() / seek(ms)` — seek reconstructs state by replaying events ≤ t
  (state = positions + votes + current speaker; cheap at this event count)
- Master clock = `AudioContext.currentTime` against the concatenated cue sheet —
  audio drives visuals, never the reverse (drift-proof)
- Event handlers: `speak` → walk to lectern (or speak from bench if `move` absent),
  bob + bubble typewriter synced to `dur_ms`; `vote_change` → sprite flash, board
  tile flip + chime, brief camera punch-in; `verdict` → all tiles reveal, gavel drop
- **Recording mode:** `?record=1` hides controls, auto-plays — screen-capture this
  at 1080p for the demo video. The courtroom IS the video.

**"The Record" — live transcript panel (REQUIRED, not stretch):** layout is a split —
courtroom canvas left (~65%), scrolling transcript panel right (~35%), court-reporter
aesthetic (monospace, timestamped, speaker-colored to match sprite accents).
- Subscribes to the same TimelinePlayer event stream — utterances append with a
  typewriter reveal as their audio plays; auto-scroll with pause-on-hover
- `vote_change` renders as a highlighted system line:
  `⚖ THE PRAGMATIST changes vote: AFFIRM → REVERSE (rd 3)`
- Click any line → `seek()` to that moment (free via player API — demo this in video)
- Running vote tally pinned at panel top (mirrors the VoteBoard)
- Works identically in replay and (stretch) SSE-live modes; it is a consumer, not a mode
- This panel is the visible proof of the tape-integrity rule: the record on screen
  IS `events.jsonl`, rendered

**Studio scene (stretch, scope-cut candidate #2):** a second Phaser scene — two anchor
sprites at a news desk with mics. During `studio` events, cut to the desk (bob + bubbles);
on `tape_ref`, wipe to the courtroom and replay the referenced event span. This makes the
full podcast watchable as a video and needs only 2 sprites + 1 background from SpriteCook.
If cut: courtroom replays the deliberation only, and the demo video layers anchor audio
over courtroom footage as narration — still works.

Build → `courtroom/dist/` → deploy to OSS static hosting.

**Claude Code build order for this module (strict):**
1. Scaffold + load a 10-event hand-written fixture (`fixtures/smoke.jsonl`) with
   placeholder rectangles. Get timing + seek correct FIRST.
2. Swap in real sprites via manifest.
3. VoteBoard + bubbles + camera.
4. Real episode data. Never debug timing and assets simultaneously.

---

## 11. Repo Layout

```
split-decision/
  CLAUDE.md  README.md  LICENSE (Apache-2.0)  .env.example
  contracts/            # case.schema.json, events.schema.json, cue_sheet.schema.json
  personas/              # 11 yaml files
  data/                  # scdb/, benchmark_manifest.json, cached case records
  scripts/               # ingest_cases.py, create_voices.py, deliberate.py,
                         # run_episode.py, run_benchmark.py, publish.py
  engine/                # deliberation chamber, foreperson, memory digests
  producer/              # script pass, tts, assembly, art, rss
  scoreboard/
  courtroom/             # Vite+Phaser app
  assets/sprites/        # SpriteCook output + manifest.json + THEME.md
  episodes/              # committed hero episodes (cache-the-wow)
  deploy/                # Function Compute config, OSS sync script (this file =
                         # proof-of-Alibaba-deployment link for submission)
  costs.jsonl
```

---

## 12. Phased Build Plan (bumwad → 5 days)

**Day 1 — Foundations & curl-before-commit (~8h)**
- [ ] Alibaba Cloud account, Model Studio activated, SINGAPORE API key, claim $40 coupon
- [ ] curl: qwen-plus chat completion ✓, qwen-max ✓
- [ ] `create_voices.py` → 10 Voice Design voices → LISTEN, iterate, lock voice_ids
- [ ] curl: qwen-image-plus one test image → OSS round-trip
- [ ] CourtListener token; `ingest_cases.py` pulls 25 decided post-cutoff + 3 pending; SCDB join
- [ ] `npx spritecook-mcp setup`; theme locked; first 2 jurist sprites; ToS/license check
- [ ] Commit all contracts (§3.3, §4, sprite manifest)
- **Gate:** every external API proven with a real call. No gate, no Day 2.

**Day 2 — Deliberation engine (~10h)**
- [ ] Clerk agent: case record → bench memo
- [ ] Chamber: state machine, private votes, statements, pair-debate, memory digests
- [ ] Events emitted to spec (t=null, sequenced)
- [ ] Run 3 full deliberations; read transcripts; tune anti-sycophancy until flips
      are argued, not announced
- **Gate:** one deliberation with ≥1 genuine, reasoned vote_change.

**Day 3 — Scoreboard + Producer (~10h)**
- [ ] `run_benchmark.py`: conditions A/B/C over 20 cases (batch overnight if needed)
- [ ] Producer: script pass → TTS → timestamps → ffmpeg episode
- [ ] First full episode audio; listen end-to-end
- [ ] Remaining SpriteCook assets (all 9 + set + props)
- **Gate:** one listenable MP3 + scoreboard numbers in hand.

**Day 4 — Courtroom + deploy (~10h)**
- [ ] Phaser build order §10 (fixture → sprites → board → real data)
- [ ] Episode art pass (Qwen-Image) + show cover; RSS live on OSS
- [ ] Function Compute deploy of `run_episode`; OSS static hosting of courtroom
- [ ] Record proof-of-deployment clip (console + live invocation)
- [ ] Run the 2–3 PENDING cases → hero episode = strongest pending case
- **Gate:** courtroom replays hero episode start-to-finish, deployed URL works.

**Day 5 — Presentation (~8h)**
- [ ] Architecture diagram (draw the §1 diagram properly — it's judged)
- [ ] 3-min video: cold-open courtroom clash → scoreboard → pending-case prediction
      → architecture → deployed URLs. Record from `?record=1` mode.
- [ ] README: problem value framing (see §13), scoreboard table, honest limitations
- [ ] Blog post (build journey → Blog Post Award, +$500)
- [ ] Devpost submission: repo, deployment proof, diagram, video, description, Track 3
- [ ] Buffer. Ship by end of July 8.

**Scope cuts, in order:** live SSE courtroom mode → 3 pending cases → 1 → episode
count 25 → 12 → pair-debate step simplifies to open floor → jurists 9 → 7 (never fewer;
keep board odd... actually keep ≥7 and odd).

---

## 13. Framing Notes (for README + video — Problem Value is 25%)

- Not a legal-advice tool. It's a research instrument + public-education artifact:
  **does structured multi-agent deliberation beat solo reasoning on hard judgment
  tasks with verifiable ground truth?** SCOTUS outcomes are one of the few public
  corpora of genuinely hard, formally adjudicated judgment calls.
- The podcast makes AI deliberation *legible to the public* — you can hear machine
  minds disagree, which is civic education about both courts and AI.
- **Two agent societies, not one:** a deliberative panel AND a newsroom that covers it.
  The journalists demonstrate a second collaboration pattern (editorial curation over
  another society's output) — and the tape-integrity rule shows agents holding agents
  accountable to a shared factual record. Lead with this in the Track 3 pitch.
- Pending-case predictions put falsifiable claims on the record — accountability
  most AI demos never risk.
- Say the contamination guard out loud. Judges who'd spot the flaw see it pre-solved.

## 14. Env Vars (`.env.example`)

```
DASHSCOPE_API_KEY=        # Model Studio, SINGAPORE region
DASHSCOPE_WORKSPACE_ID=
COURTLISTENER_TOKEN=
SPRITECOOK_API_KEY=       # build-time only
OSS_ACCESS_KEY_ID=
OSS_ACCESS_KEY_SECRET=
OSS_BUCKET=split-decision
OSS_REGION=ap-southeast-1
```
