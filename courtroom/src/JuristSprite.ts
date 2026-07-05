import Phaser from "phaser";
import type { SpriteEntry } from "./manifest";
import type { Persona } from "./personas";
import type { Place } from "./types";

// One juror on the bench. Backed by a real sprite sheet when the manifest has one
// (textualist, pragmatist today), otherwise a coloured placeholder rectangle in the
// persona's accent — so the panel is complete before every sprite exists. The container
// is the positioned unit; the bob applied while speaking rides on the inner visual only,
// so it never fights the walk tween.

const WALK_MS = 650;

// Depth bands: bench-seated jurists sit between the backdrop (-9) and the bench-front
// overlay (2); a jurist at the lectern walks in front of the bench (5). Nameplates ride
// on their own layer (4) so the overlay never hides them.
const DEPTH_BENCH = 0;
const DEPTH_FLOOR = 5;
const DEPTH_PLATE = 4;

/** Transparent rows under the art in frame 0 (smart-crop padding below the feet). */
function measureBottomPad(
  scene: Phaser.Scene,
  textureKey: string,
  frameW: number,
  frameH: number,
): number {
  for (let y = frameH - 1; y >= 0; y--) {
    for (let x = 0; x < frameW; x += 2) {
      if (scene.textures.getPixelAlpha(x, y, textureKey, 0) > 0) {
        return frameH - 1 - y;
      }
    }
  }
  return 0;
}

export class JuristSprite {
  readonly container: Phaser.GameObjects.Container;
  private readonly plate: Phaser.GameObjects.Container;
  private readonly visual: Phaser.GameObjects.Sprite | Phaser.GameObjects.Rectangle;
  private readonly hasSheet: boolean;
  private readonly idleKey: string;
  private readonly walkKey: string;
  private visualBaseY: number;
  private readonly frameH: number;
  private bottomPad = 0;
  private plateEnabled = true;

  private home = { x: 0, y: 0 };
  private lectern = { x: 0, y: 0 };
  private place: Place = "bench";
  private speaking = false;
  private walkTween?: Phaser.Tweens.Tween;
  private bob = 0;

  constructor(
    private readonly scene: Phaser.Scene,
    readonly persona: Persona,
    entry: SpriteEntry | undefined,
    seatW: number,
  ) {
    this.hasSheet = !!entry && scene.textures.exists(`${persona.id}-idle`);
    this.idleKey = `${persona.id}-idle`;
    this.walkKey = `${persona.id}-walk`;
    this.frameH = entry?.frame_h ?? 0;

    const accent = Phaser.Display.Color.HexStringToColor(persona.accent).color;

    if (this.hasSheet && entry) {
      const spr = scene.add.sprite(0, 0, this.idleKey, 0);
      spr.setScale(Math.min(1, (seatW * 0.9) / entry.frame_w));
      spr.setOrigin(0.5, 1);
      // Sheets are smart-cropped per character, so some frames carry transparent
      // rows under the feet; anchoring the FRAME bottom to the bench baseline then
      // leaves that jurist floating above colleagues. Measure the art's real bottom
      // so feet, not frame edges, land on the baseline.
      this.bottomPad = measureBottomPad(scene, this.idleKey, entry.frame_w, entry.frame_h);
      this.visual = spr;
      this.visualBaseY = 0;
      spr.play(this.idleKey);
    } else {
      const w = Math.min(64, seatW * 0.7);
      const h = w * 1.4;
      const rect = scene.add.rectangle(0, -h / 2, w, h, accent, 1);
      rect.setStrokeStyle(2, 0x000000, 0.35);
      rect.setOrigin(0.5, 0.5);
      this.visual = rect;
      this.visualBaseY = -h / 2;
    }

    const label = scene.add
      .text(0, 6, persona.short, {
        fontFamily: "ui-monospace, monospace",
        fontSize: "11px",
        color: "#e8e0d2",
        align: "center",
      })
      .setOrigin(0.5, 0);

    const nameplate = scene.add.rectangle(0, 4, seatW * 0.92, 18, accent, 0.28).setOrigin(0.5, 0);
    nameplate.setStrokeStyle(1, accent, 0.6);

    this.container = scene.add.container(0, 0, [this.visual]).setDepth(DEPTH_BENCH);
    this.plate = scene.add.container(0, 0, [nameplate, label]).setDepth(DEPTH_PLATE);
  }

  /** Rescale to a target on-screen height (bench-art proportions); 0 keeps frame size. */
  setDisplayHeight(h: number): void {
    if (h <= 0) return;
    if (this.hasSheet && this.frameH > 0) {
      const contentH = this.frameH - this.bottomPad;
      const scale = h / Math.max(1, contentH);
      (this.visual as Phaser.GameObjects.Sprite).setScale(scale);
      // Drop the frame so the art's lowest opaque row — the feet — hits the baseline.
      this.visualBaseY = this.bottomPad * scale;
      this.visual.setY(this.visualBaseY);
    } else {
      const rect = this.visual as Phaser.GameObjects.Rectangle;
      rect.setSize(h / 1.4, h);
      this.visualBaseY = -h / 2;
      rect.setY(this.visualBaseY);
    }
  }

  /** Show/hide the whole unit (sprite + nameplate) — used by the studio/courtroom cut. */
  setVisible(on: boolean): void {
    this.container.setVisible(on);
    this.plate.setVisible(on && this.plateEnabled);
  }

  /** Permanently drop the nameplate (studio anchors — the desk has no plate rail). */
  disablePlate(): void {
    this.plateEnabled = false;
    this.plate.setVisible(false);
  }

  /** Render only the top `fraction` of the frame — a seated figure's torso; the legs
   * end cleanly at the crop line instead of dangling behind the set. */
  setCropBottom(fraction: number): void {
    if (this.hasSheet) {
      const spr = this.visual as Phaser.GameObjects.Sprite;
      spr.setCrop(0, 0, spr.frame.width, spr.frame.height * fraction);
    }
  }

  /** Override the depth band (studio anchors render above the studio backdrop). */
  setBaseDepth(depth: number): void {
    this.container.setDepth(depth);
    this.plate.setDepth(depth + 1);
  }

  setSeat(x: number, y: number): void {
    this.home = { x, y };
    if (this.place === "bench" && !this.walkTween?.isPlaying()) {
      this.container.setPosition(x, y);
      this.plate.setPosition(x, y);
    }
  }

  setLectern(x: number, y: number): void {
    this.lectern = { x, y };
  }

  /** Where the speech bubble should anchor (top of the visual, in scene coords). */
  get bubbleAnchor(): { x: number; y: number } {
    const topOffset = this.hasSheet
      ? -(this.visual as Phaser.GameObjects.Sprite).displayHeight - 6
      : this.visualBaseY - (this.visual as Phaser.GameObjects.Rectangle).height / 2 - 6;
    return { x: this.container.x, y: this.container.y + topOffset };
  }

  setSpeaking(on: boolean): void {
    if (on === this.speaking) return;
    this.speaking = on;
    if (!on) {
      this.bob = 0;
      this.visual.setY(this.visualBaseY);
    }
  }

  /** Snap immediately to a place (used on seek — no animation). */
  snapTo(place: Place): void {
    this.walkTween?.stop();
    this.walkTween = undefined;
    this.place = place;
    this.container.setDepth(place === "bench" ? DEPTH_BENCH : DEPTH_FLOOR);
    const target = place === "lectern" ? this.lectern : this.home;
    this.container.setPosition(target.x, target.y);
    if (this.hasSheet) (this.visual as Phaser.GameObjects.Sprite).play(this.idleKey, true);
  }

  /** Animate to a place (used during forward playback). */
  walkTo(place: Place): void {
    if (place === this.place && !this.walkTween?.isPlaying()) return;
    this.place = place;
    // Leaving the bench means stepping in front of it (above the bench overlay).
    this.container.setDepth(place === "bench" ? DEPTH_BENCH : DEPTH_FLOOR);
    const target = place === "lectern" ? this.lectern : this.home;
    if (this.hasSheet) (this.visual as Phaser.GameObjects.Sprite).play(this.walkKey, true);
    this.walkTween?.stop();
    this.walkTween = this.scene.tweens.add({
      targets: this.container,
      x: target.x,
      y: target.y,
      duration: WALK_MS,
      ease: "Sine.InOut",
      onComplete: () => {
        if (this.hasSheet) (this.visual as Phaser.GameObjects.Sprite).play(this.idleKey, true);
      },
    });
  }

  update(_dt: number, timeMs: number): void {
    this.plate.setPosition(this.container.x, this.container.y);
    if (this.speaking) {
      this.bob = Math.sin(timeMs / 140) * 3;
      this.visual.setY(this.visualBaseY + this.bob);
    }
  }
}
