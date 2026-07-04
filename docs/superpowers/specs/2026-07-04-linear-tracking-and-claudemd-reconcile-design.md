# Design: Linear-build tracking + CLAUDE.md reconciliation

**Date:** 2026-07-04
**Status:** Approved (brainstorm session, 2026-07-04)
**Authority document:** `docs/Qwen Cloud Proof of Deployment.md` (official hackathon
requirements — wins every conflict with CLAUDE.md)

## Goal

1. Reconcile `CLAUDE.md` (the engineering blueprint) with the official Qwen Cloud
   deployment/requirements doc, which contradicts it on deployment target, model IDs,
   API endpoint, TTS model, and token budget.
2. Establish Linear (via the `linear-build` plugin) as the project-tracking source of
   truth, with a project + milestones + per-module issues derived from the CLAUDE.md
   Day 1–5 build plan.

## Decisions made (with rationale)

| Decision | Choice | Why |
|---|---|---|
| Deployment target | **SAS (Simple Application Server) + OSS** | The official doc documents only ECS and SAS proof paths; proof = Workbench Overview screenshot of the running project. SAS is the doc's fast path (<5 min deploy, systemd service). Function Compute is dropped — no documented proof path. OSS keeps its static-hosting role (podcast, RSS, courtroom app). |
| CLAUDE.md update scope | **Full reconcile** | CLAUDE.md is the blueprint; building against wrong model IDs on Day 1 burns hours. All stale facts updated now, with one open question flagged (voice creation, below). |
| Linear issue granularity | **Per-module (~12 issues)** | Each issue is independently buildable and verifiable, matching how linear-build runs its verification gate. Per-day is too coarse to verify; per-task (~35) is too much overhead for a 5-day solo sprint. |

## Part 1 — CLAUDE.md changes

### Facts to update (old → new)

| Item | Old (CLAUDE.md) | New (per official doc) |
|---|---|---|
| Juror model | `qwen-plus` | `qwen3.7-plus` |
| Foreperson/Clerk model | `qwen-max` | `qwen3.7-max` |
| Cheap tier | (none) | `qwen3.6-flash` noted as available for low-stakes calls |
| API endpoint | Workspace-specific Model Studio URL (`{WorkspaceId}.ap-southeast-1.maas.aliyuncs.com`) via dashscope SDK | OpenAI-compatible `https://dashscope-intl.aliyuncs.com/compatible-mode/v1` via `openai` SDK |
| TTS | "Qwen3-TTS via Model Studio Voice Design" | `cosyvoice-v3-plus` — see open question below |
| Budget | "$40 coupon" | 70M+ free tokens for new accounts. Per-call cost logging to `costs.jsonl` retained (still good hygiene; free tier is finite) |
| Deploy target | Function Compute (pipeline) + OSS (static) | SAS (pipeline runner as systemd service) + OSS (static). Proof = Workbench Overview screenshot |

### Sections touched

- **§0 Prime Directives:** directive 5 (budget) reworded around the free-token pool;
  cost logging retained.
- **§1 System Architecture:** diagram footer + "Deploy targets" block — Function
  Compute → SAS; proof-of-deployment line references the Workbench screenshot and the
  authority doc.
- **§2 Tech Stack:** model rows, TTS row, endpoint boilerplate (OpenAI SDK snippet
  replaces dashscope snippet).
- **§7 Deliberation Protocol:** token-budget paragraph updated to free-tier framing.
- **§12 Phased Build Plan:** Day 1 curl checks use new model IDs; Day 4 deploy tasks
  rewritten for SAS (create instance, systemd unit for pipeline runner, capture
  Workbench screenshot).
- **§14 Env Vars:** add `DASHSCOPE_BASE_URL`; remove `DASHSCOPE_WORKSPACE_ID`.
- **NEW §15 Project Tracking:** states that all build work is tracked in Linear via
  `/linear-build:linear-build`; the Linear project is the source of truth for status;
  issues carry Intent / Acceptance / Verification; Day gates = Linear milestones;
  `docs/Qwen Cloud Proof of Deployment.md` is the submission-requirements authority.

### Explicitly NOT changed

Deliberation protocol, personas, event schema/contracts, anti-sycophancy machinery,
scope-cut order, contamination guard, repo layout. No conflict with the official doc.

### Open question (flagged in CLAUDE.md, resolved by Issue 1/2 on Day 1)

CLAUDE.md's voice plan assumed "Voice Design" (create 12 custom voices from text
prompts). The official doc lists `cosyvoice-v3-plus` for TTS but does not document
custom-voice creation. Day 1 must curl-verify what voice/timbre control cosyvoice
offers. Fallback: select 12 maximally distinct built-in voices/timbres; the
"distinguishable blind" quality bar from the PRD still applies.

## Part 2 — Linear project structure

- **Project:** "Split Decision — Qwen Hackathon" · target date 2026-07-08
- **Milestones (5):** Day 1–5, named after the CLAUDE.md gates:
  1. Day 1 — Every external API proven with a real call
  2. Day 2 — One deliberation with ≥1 genuine, reasoned vote_change
  3. Day 3 — One listenable MP3 + scoreboard numbers in hand
  4. Day 4 — Courtroom replays hero episode; deployed URL works; proof captured
  5. Day 5 — Submission shipped (video, README, Devpost)
- **Issues (~12), per-module.** Each carries: Intent (one paragraph), Acceptance
  (the relevant CLAUDE.md checklist items), Verification (how the gate is proven).

| # | Issue | Milestone | Acceptance sketch |
|---|---|---|---|
| 1 | Qwen Cloud setup + curl-verify all model IDs | Day 1 | Account + API key; successful completions on `qwen3.7-plus`, `qwen3.7-max`, `qwen3.6-flash` via OpenAI-compatible endpoint; confirms/corrects the reconciled CLAUDE.md facts against the live API |
| 2 | Voice pipeline: 12 distinct voices (cosyvoice-v3-plus) | Day 1 | Voice-creation capability verified; 12 voices generated; blind listen test passed; voice IDs locked into persona YAMLs; anchors designed first |
| 3 | Image gen test → OSS round-trip | Day 1 | One `qwen-image-2.0-pro` (or `wan2.6-t2i`) image generated, downloaded, pushed to OSS |
| 4 | Case ingestion + contamination-guarded manifest | Day 1 | CourtListener token works; 25 decided post-2025-06 cases + 3 pending pulled; SCDB joined; `benchmark_manifest.json` committed with rationale |
| 5 | SpriteCook setup + theme + first sprites | Day 1 | MCP configured; THEME.md locked; 2 jurist sprites; ToS/license confirmed (fallback Kenney CC0) |
| 6 | Contracts committed | Day 1 | `case.schema.json`, `events.schema.json`, `cue_sheet.schema.json` committed |
| 7 | Deliberation engine | Day 2 | Clerk bench memo; chamber state machine per §7; events to spec (t=null, sequenced); 3 tuned runs; ≥1 argued (not announced) vote flip |
| 8 | Scoreboard benchmark A/B/C | Day 3 | `run_benchmark.py` runs all three conditions over ≥12 (target 20) cases; `results.json` + README table; honest reporting if C ≤ B |
| 9 | Producer pipeline | Day 3 | Clip manifest → two-way script → TTS → timestamps → ffmpeg MP3; tape-integrity rule enforced (clips by event index); one listenable episode |
| 10 | Courtroom renderer | Day 4 | Phaser build order §10 followed (fixture first); TimelinePlayer with seek; VoteBoard; The Record panel with click-to-seek; `?record=1` mode |
| 11 | SAS deploy + OSS hosting + proof screenshot | Day 4 | Pipeline runner live on SAS as systemd service; courtroom + RSS on OSS; Workbench Overview screenshot captured per `docs/Qwen Cloud Proof of Deployment.md` |
| 12 | Presentation package | Day 5 | 3-min video from `?record=1`; architecture diagram; README with scoreboard + limitations; blog post; Devpost submission (Track 3) |

Issue 1 blocks issues 2–4 (needs the API key). Issues 2–6 are otherwise parallel.
Issue 7 blocks 8–9. Issues 8/9/10 are parallel. Issue 11 needs 9–10 output. Issue 12
needs everything.

## Implementation sequence

1. Edit CLAUDE.md per Part 1 (single commit: `docs: reconcile CLAUDE.md with official deployment doc; add Linear tracking`)
2. Invoke `/linear-build:linear-build` to create the project, milestones, and the 12
   issues per Part 2 (this replaces the generic writing-plans step — linear-build is
   the chosen tracking/build vehicle)

## Error handling / risks

- If live API rejects `qwen3.7-*` IDs (doc drift), Issue 1's verification catches it
  Day 1; CLAUDE.md gets a follow-up correction commit.
- If cosyvoice has no custom-voice creation, Issue 2's fallback (distinct built-in
  voices) keeps the PRD quality bar without schedule impact.
- Linear team/workspace selection happens at linear-build invocation time (user has
  one workspace; confirm team interactively if multiple).
