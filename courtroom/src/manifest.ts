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
    // Set pieces (courtroom_bg, lectern, news_desk) share the manifest but have no
    // animation sheets — they'd crash the spritesheet preload loop.
    if (!value || typeof value !== "object" || !("sheets" in value)) continue;
    out[key] = value as SpriteEntry;
  }
  return out;
}

/** A static set-piece image (bg, lectern, news desk) from the manifest's set_pieces. */
export function setPieceFile(raw: Record<string, unknown>, key: string): string | null {
  const pieces = raw["set_pieces"];
  if (!pieces || typeof pieces !== "object") return null;
  const entry = (pieces as Record<string, unknown>)[key];
  if (entry && typeof entry === "object" && "file" in entry) {
    return (entry as { file: string }).file;
  }
  return null;
}
