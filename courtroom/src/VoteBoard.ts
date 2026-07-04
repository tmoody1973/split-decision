import Phaser from "phaser";
import { JURIST_ORDER, personaFor } from "./personas";
import type { Position } from "./types";

const COLORS = {
  unknown: 0x4b4436,
  affirm: 0x2f7d4f,
  reverse: 0xa83a3a,
};

// The nine-tile tally at the foot of the stage. setVotes() snaps colours (seek); flip()
// plays the wow beat — a card-flip scale on a single tile with an accent flash — when a
// vote_change crosses the playhead during forward playback.
export class VoteBoard {
  private tiles: Phaser.GameObjects.Rectangle[] = [];
  private glyphs: Phaser.GameObjects.Text[] = [];
  private readonly container: Phaser.GameObjects.Container;
  private state: Record<string, Position | "unknown"> = {};
  private flipping = new Set<string>();

  constructor(private readonly scene: Phaser.Scene) {
    this.container = scene.add.container(0, 0);
    JURIST_ORDER.forEach((id, i) => {
      const tile = scene.add.rectangle(0, 0, 40, 40, COLORS.unknown, 1).setOrigin(0.5);
      tile.setStrokeStyle(2, 0x000000, 0.4);
      const glyph = scene.add
        .text(0, 0, initials(personaFor(id).display), {
          fontFamily: "ui-monospace, monospace",
          fontSize: "12px",
          color: "#f0ead9",
          fontStyle: "bold",
        })
        .setOrigin(0.5);
      this.tiles[i] = tile;
      this.glyphs[i] = glyph;
      this.container.add([tile, glyph]);
    });
  }

  layout(x: number, y: number, width: number): void {
    const n = JURIST_ORDER.length;
    const size = Math.min(48, width / (n + 2));
    const gap = (width - size * n) / (n - 1);
    JURIST_ORDER.forEach((_, i) => {
      const cx = x + size / 2 + i * (size + gap);
      this.tiles[i].setSize(size, size).setPosition(cx, y);
      this.glyphs[i].setPosition(cx, y);
    });
  }

  // Snap tiles to the given votes, but leave any tile mid-flip alone so its card-flip
  // reveal isn't overwritten before it lands.
  setVotes(votes: Record<string, Position | "unknown">): void {
    JURIST_ORDER.forEach((id, i) => {
      if (this.flipping.has(id)) return;
      const v = votes[id] ?? "unknown";
      this.state[id] = v;
      this.tiles[i].setFillStyle(COLORS[v]);
    });
  }

  flip(agent: string, to: Position): void {
    const i = JURIST_ORDER.indexOf(agent as (typeof JURIST_ORDER)[number]);
    if (i < 0) return;
    const tile = this.tiles[i];
    this.state[agent] = to;
    this.flipping.add(agent);
    this.scene.tweens.add({
      targets: tile,
      scaleX: 0,
      duration: 130,
      yoyo: true,
      ease: "Quad.In",
      onYoyo: () => tile.setFillStyle(COLORS[to]),
      onComplete: () => this.flipping.delete(agent),
    });
    // Accent flash ring.
    const ring = this.scene.add
      .rectangle(tile.x, tile.y, tile.width + 8, tile.height + 8)
      .setStrokeStyle(3, 0xf0d79a, 1)
      .setFillStyle();
    this.scene.tweens.add({
      targets: ring,
      alpha: 0,
      scaleX: 1.4,
      scaleY: 1.4,
      duration: 600,
      ease: "Cubic.Out",
      onComplete: () => ring.destroy(),
    });
  }
}

function initials(display: string): string {
  const core = display.replace(/^The\s+/, "");
  const parts = core.split(/\s+/);
  if (parts.length === 1) return core.slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}
