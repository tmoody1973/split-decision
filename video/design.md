# Split Decision — demo video design system

The video inherits the app's pixel register verbatim. Reference implementations:
`courtroom/findings.html`, `courtroom/index.html`, `courtroom/src/archDiagram.ts`.

## Palette

| Token    | Hex       | Use                                    |
| -------- | --------- | -------------------------------------- |
| bg       | `#1a140d` | scene backgrounds                      |
| panel    | `#241a10` | cards, chips, panels                   |
| line     | `#4a3320` | hairline rules, panel borders          |
| wood     | `#8a5a2b` | structural accents                     |
| ink      | `#e8e0d2` | primary text                           |
| muted    | `#9a8f7d` | secondary text, metadata               |
| gold     | `#caa24a` | accent, bars, borders                  |
| gold-hi  | `#f0d79a` | display headlines, highlights          |
| navy     | `#1e2a4a` | studio/journalist register (dark)      |
| navy-hi  | `#3a5a9a` | studio register (bright)               |
| burgundy | `#7a1f2b` | reverse votes, negative results        |
| green    | `#3f6d4e` | affirm votes, positive chips           |

## Typography

- Single family: `ui-monospace, Menlo, monospace` — the product's own register.
- Bold everywhere; labels letter-spaced (`0.12em+`) uppercase smallcaps-style.
- Display: 96–150px. Body: 28–40px. Labels/metadata: 20–24px.
- `font-variant-numeric: tabular-nums` on all stat values.

## Shape language

- 3px hard borders (`#000` or `line`), zero border-radius.
- Hard offset shadows: `4px 4px 0 #000a` (6px 6px on large cards). No blur shadows.
- Colored header bars on cards (navy for studio, gold/wood for court).
- `image-rendering: pixelated` on any product imagery.

## Motion register

- Rhythm (locked in spec): TAPE-fast-DIAGRAM-hold-CUT-fast-BARS-slow-hold-CLOSE.
- Hard cuts between product footage (matches the product's own editing).
- Push slides / blur crossfades into native scenes. One shaderless system.
- Entrances: stamps (back.out), slides (power3.out), draws (expo.out). No bounce.

## What NOT to do

- No border-radius, no soft gradients, no glassmorphism.
- No fonts other than the mono stack.
- No colors outside this palette.
- Never paraphrase product tape — overlays annotate, they never re-voice.
