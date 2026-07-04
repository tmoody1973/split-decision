// Shape of assets/sprites/manifest.json. Only some jurists have sheets today; the rest
// are absent and fall back to coloured rectangles at runtime (graceful degradation —
// sprites arrive later without any renderer change).

export interface SpriteEntry {
  sheets: { idle: string; walk: string };
  base: string;
  frame_w: number;
  frame_h: number;
  fps: number;
  anims: { idle: number[]; walk: number[] };
  palette_accent: string;
}

export type SpriteManifest = Record<string, SpriteEntry>;

export function parseManifest(raw: Record<string, unknown>): SpriteManifest {
  const out: SpriteManifest = {};
  for (const [key, value] of Object.entries(raw)) {
    if (key.startsWith("_")) continue; // "_format" doc key
    out[key] = value as SpriteEntry;
  }
  return out;
}
