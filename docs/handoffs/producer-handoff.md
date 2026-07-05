# Handoff: Podcast Producer (MOO-224)

For a fresh context window building the producer pipeline. Read CLAUDE.md §9
(the spec) + this doc (the field knowledge). Track work on Linear issue MOO-224.

## What exists (don't rebuild)

- **25 deliberation episodes** in `episodes/{case_id}/events.jsonl` — schema-valid,
  `t: null` (YOU fill timestamps after TTS). 24 count for the scoreboard; the 3
  oldest (Sripetch `cl-cluster-10870059`, Keathley `cl-cluster-10873663`, Pung
  `cl-cluster-10878534`) are protocol-v1; the rest are v2 (fact-anchored).
  **Pung is the best episode**: 9 flips, 5 rounds, verdict 5-4 reverse, real
  outcome reverse 9-0 (a MATCH), transcript.md alongside it.
- **12 locked voices** — `voice_id` in every `personas/*.yaml`. Previews in
  `assets/voice_previews/` (listen-approved).
- **Publishing helpers** in `scripts/oss_publish.py`: `publish_bytes`,
  `publish_url`, `generate_image_to_oss` (art pass). Bucket `split-decision`
  (ap-southeast-1, public-read, Block Public Access already disabled).
- **LLM helpers** in `engine/llm.py` (`chat`, `chat_json`, cost logging — use them;
  every call must land in costs.jsonl). `scripts/qwen_client.py` has `.env` loading.
- **Cue sheet contract**: `contracts/cue_sheet.schema.json` — array of
  `{t, stream: "deliberation"|"studio", event_index, audio_file, dur_ms}`,
  ordered by t. The courtroom player (courtroom/) consumes it; its clock has an
  AudioClock seam waiting for real timestamps.

## Hard-won API facts (each cost hours — trust these)

1. **TTS synthesis**: POST `https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation`
   body `{"model": "qwen3-tts-vd-2026-01-26", "input": {"text": ..., "voice": "<voice_id from persona yaml>"}}`
   → `output.audio.url` (WAV, expires ~24h — download immediately, convert to mp3
   via ffmpeg). Verified working 2026-07-04. The hackathon doc's cosyvoice snippet
   is WRONG for intl (Beijing-only). Voice creation (already done) used
   `/services/audio/tts/customization` with `qwen-voice-design`.
2. **Image gen**: `wan2.6-t2i` ONLY works on the sync multimodal route (see
   `generate_image_to_oss`); OpenAI `/images` 404s; async text2image rejects it.
   Show cover: `qwen-image-2.0-pro` (renders text). **Prompt rule: describe the
   SCENE, never crime/violence — `data_inspection_failed` moderation is real and
   killed a benchmark case.** Wrap all model calls in try/except for it.
3. **Reasoning models burn ~8-11× naive token estimates** (hidden reasoning
   tokens). Anchors' script pass on qwen3.7-plus is fine; budget is healthy
   (~26M of 70M used).
4. `contracts/events.schema.json` vote_split allows `"unknown"` (reveal events).

## Build order (per CLAUDE.md §9, refined)

1. **Clip selection** (qwen3.7-plus): transcript → `clip_manifest.json`, spans of
   event INDICES (0-based line index into events.jsonl). TAPE INTEGRITY: never
   rewrite juror text. Cold open = sharpest exchange; every vote_change + trigger;
   verdict; reveal.
2. **Two-way anchor script** → `episodes/{id}/studio_events.jsonl` (`studio` +
   `tape_ref` events per contract §4). anchor_lead explains law, anchor_analyst
   reads the room; they reference each other. Include the scoreboard check-in:
   final season stats are in `scoreboard/results.json` (A 83% / B 77.4% / C 66.7%
   — the honest "great arguments, worse predictions" story is ON BRAND, use it).
3. **TTS pass**: every deliberation event with text + every studio event →
   `utt_NNN.mp3` / `studio_NNN.mp3` in the episode dir. ffprobe for dur_ms.
4. **Timestamp pass**: fill `t` in both streams (300ms gaps), write cue_sheet.json.
   Validate everything against the contracts (scripts/validate_events.py).
5. **Assembly**: ffmpeg concat + CC0 music bed ducked −14dB under studio segments
   (commit the bed's license note). Target 12–18 min. LISTEN before calling done.
6. **Art + publish**: episode art via `generate_image_to_oss` (style: "hand-drawn
   courtroom sketch, warm pastel, loose ink lines"); upload MP3; write feed.xml
   (RSS 2.0 + podcast namespace) → OSS. Episode page links the courtroom replay.

## Gotchas

- Foreperson/verdict/reveal events have no `audio_file` yet — verdict/reveal can be
  read by an anchor instead of TTS'd from the chamber; foreperson HAS a voice.
- 12 voices were never heard TOGETHER — if two sound close in the mix, regeneration
  costs $0.20 (cap 5, quota notes on MOO-217).
- Commit hero assets to `episodes/` (cache-the-wow) AND push to OSS.
- Suncor/Younge/Prutehi (pending, `oyez-*.json`) still need deliberations run for
  the hero "prediction" episode (MOO-226) — the producer pipeline should work on
  any episode dir, Pung first.
