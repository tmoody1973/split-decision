# Split Decision — Sprite Theme (locked 2026-07-04)

Every SpriteCook asset references this register. Do not restyle mid-project.

## Style prompt (prepend to every generation)

> 16-bit courtroom drama. Warm wood tones, deep judicial navy and burgundy robes,
> soft key light from tall windows. Dignified but slightly caricatured proportions,
> readable at 96px. Clean pixel grid, no anti-aliasing, transparent background.

## Rules

- Characters: 96×96 frames, side-view stage orientation, feet on a consistent
  baseline so all jurists line up on the bench.
- Animations per jurist: **idle** (2–4 frames) and **walk** (4 frames) ONLY.
  Talking is code-side (bubble + bob) — never generate talk frames (scope trap).
- Each jurist gets one accent color (robe trim / tie / scarf) matching
  `palette_accent` in `manifest.json` — The Record panel and VoteBoard reuse it.
- Set pieces (bench, gallery, lectern, vote board) are separate layers, generated
  individually against the same style prompt.
- Style continuity: reuse the first accepted jurist sprite as `style_asset_ids`
  reference for every subsequent generation (SpriteCook's reference mechanism).

## Cast diversity (required — Tarik, 2026-07-04)

The bench reflects a diverse panel. At least three characters are African-American;
assigned (bake these into the generation prompts for the remaining sprites):

- **foreperson** — Black woman in her 60s, presiding presence (matches her low-contralto voice)
- **originalist** — Black man in his 50s, professorial
- **civil_libertarian** — Black woman in her 30s, earnest energy

Remaining cast varies across ethnicity, age, and build; no two silhouettes alike
(sprites must be distinguishable at 96px, same bar as the voices).

## Persona accent palette

| persona | accent |
|---|---|
| textualist | #7a1f2b (oxblood) |
| originalist | #5b4a2f (sepia brown) |
| living_constitutionalist | #2e6f5e (teal green) |
| pragmatist | #c27b2c (amber) |
| precedent_maximalist | #4a4e69 (slate violet) |
| federalism_hawk | #8c3b00 (burnt orange) |
| civil_libertarian | #2b6cb0 (bright blue) |
| process_formalist | #6b7280 (cool gray) |
| minimalist | #9b8ec4 (soft lavender) |
| foreperson | #1f2a44 (deep navy) |
| anchor_lead | #b23a48 (broadcast red) |
| anchor_analyst | #3a7ca5 (steel blue) |
