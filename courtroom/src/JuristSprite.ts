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

export class JuristSprite {
  readonly container: Phaser.GameObjects.Container;
  private readonly visual: Phaser.GameObjects.Sprite | Phaser.GameObjects.Rectangle;
  private readonly hasSheet: boolean;
  private readonly idleKey: string;
  private readonly walkKey: string;
  private readonly visualBaseY: number;

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

    const accent = Phaser.Display.Color.HexStringToColor(persona.accent).color;

    if (this.hasSheet && entry) {
      const spr = scene.add.sprite(0, 0, this.idleKey, 0);
      const scale = Math.min(1, (seatW * 0.9) / entry.frame_w);
      spr.setScale(scale);
      spr.setOrigin(0.5, 1);
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

    this.container = scene.add.container(0, 0, [nameplate, this.visual, label]);
  }

  setSeat(x: number, y: number): void {
    this.home = { x, y };
    if (this.place === "bench" && !this.walkTween?.isPlaying()) {
      this.container.setPosition(x, y);
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
    const target = place === "lectern" ? this.lectern : this.home;
    this.container.setPosition(target.x, target.y);
    if (this.hasSheet) (this.visual as Phaser.GameObjects.Sprite).play(this.idleKey, true);
  }

  /** Animate to a place (used during forward playback). */
  walkTo(place: Place): void {
    if (place === this.place && !this.walkTween?.isPlaying()) return;
    this.place = place;
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
    if (this.speaking) {
      this.bob = Math.sin(timeMs / 140) * 3;
      this.visual.setY(this.visualBaseY + this.bob);
    }
  }
}
