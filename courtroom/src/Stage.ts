import Phaser from "phaser";

// Static set dressing + the responsive layout math the scene reuses. Purely presentational:
// wood-toned backdrop, a bench band, a lectern, and the anchor points every dynamic object
// (jurors, vote board) is positioned against. layout() is re-run on every resize.

export interface StageLayout {
  seatY: number;
  seatW: number;
  seatX: (i: number) => number;
  /** Target on-screen jurist height; 0 = keep the sprite's own frame-based size. */
  spriteH: number;
  lectern: { x: number; y: number };
  board: { x: number; y: number; width: number };
}

// Image-relative anchors measured off the bench art (see assets/sprites/set_courtroom_bg.png):
// nine chairs evenly spaced, bench-top line, and where a seated jurist's feet baseline sinks
// to so the bench-front overlay occludes their lower body.
const BG_FIRST_SEAT_X = 0.113;
const BG_SEAT_STEP = 0.0968;
const BG_BENCH_TOP = 0.592; // top edge of the bench rail — overlay crop starts here
const BG_SEAT_BASELINE = 0.648; // feet sink this far, so the rail occludes the lower body
const BG_SPRITE_H = 0.3;

const SEATS = 9;
const SIDE_PAD = 48;

export class Stage {
  private readonly g: Phaser.GameObjects.Graphics;
  private readonly bg: Phaser.GameObjects.Image | null;
  private readonly benchFront: Phaser.GameObjects.Image | null;
  private readonly title: Phaser.GameObjects.Text;
  private readonly lecternRect: Phaser.GameObjects.Rectangle;
  private readonly boardLabel: Phaser.GameObjects.Text;

  constructor(scene: Phaser.Scene, title = "SPLIT DECISION — THE CHAMBER") {
    // The pixel-art courtroom backdrop (16-bit bench for nine), when its texture loaded.
    // The flat graphics backdrop stays underneath as a letterbox fill. benchFront is a
    // cropped re-render of the same image (bench-top line downward) drawn ABOVE the
    // jurists, so a jurist whose baseline sinks below the bench top reads as seated
    // behind it — the sprites live between the two layers.
    this.bg = scene.textures.exists("courtroom_bg")
      ? scene.add.image(0, 0, "courtroom_bg").setOrigin(0.5, 0.5).setDepth(-9)
      : null;
    this.benchFront = this.bg
      ? scene.add.image(0, 0, "courtroom_bg").setOrigin(0.5, 0.5).setDepth(2)
      : null;
    this.g = scene.add.graphics().setDepth(-10);
    this.title = scene.add
      .text(0, 12, title, {
        fontFamily: "ui-monospace, monospace",
        fontSize: "13px",
        color: "#9a8f7d",
        fontStyle: "bold",
      })
      .setOrigin(0.5, 0)
      .setDepth(5);
    this.lecternRect = scene.add.rectangle(0, 0, 90, 70, 0x5b3d22, 1).setDepth(3);
    this.lecternRect.setStrokeStyle(3, 0x3a2614, 1);
    this.boardLabel = scene.add
      .text(0, 0, "THE VOTE", {
        fontFamily: "ui-monospace, monospace",
        fontSize: "10px",
        color: "#9a8f7d",
      })
      .setOrigin(0.5, 1)
      .setDepth(5);
  }

  layout(width: number, height: number): StageLayout {
    let seatY: number;
    let seatW: number;
    let seatX: (i: number) => number;
    let spriteH = 0;
    let lectern: { x: number; y: number };

    if (this.bg && this.benchFront) {
      // Fit the art to the canvas width (cover-scaling crops the outer chairs on
      // narrow canvases), pinned to the top; the flat floor fill shows beneath on tall
      // canvases. All jurist anchors are image-relative (see BG_* constants).
      const scale = width / this.bg.width;
      const center: [number, number] = [width / 2, (this.bg.height * scale) / 2];
      this.bg.setScale(scale).setPosition(...center);
      this.benchFront
        .setScale(scale)
        .setPosition(...center)
        .setCrop(0, this.bg.height * BG_BENCH_TOP, this.bg.width, this.bg.height);
      const dw = this.bg.displayWidth;
      const dh = this.bg.displayHeight;
      seatY = dh * BG_SEAT_BASELINE;
      seatW = dw * BG_SEAT_STEP;
      spriteH = dh * BG_SPRITE_H;
      seatX = (i: number) => dw * (BG_FIRST_SEAT_X + i * BG_SEAT_STEP);
      lectern = { x: width / 2, y: Math.min(height * 0.82, dh * 0.84) };
    } else {
      seatY = Math.max(150, height * 0.34);
      const usable = width - SIDE_PAD * 2;
      seatW = usable / SEATS;
      seatX = (i: number) => SIDE_PAD + seatW / 2 + i * seatW;
      lectern = { x: width / 2, y: height * 0.6 };
    }
    const board = { x: SIDE_PAD, y: height * 0.86, width: width - SIDE_PAD * 2 };

    // Backdrop.
    this.g.clear();
    this.g.fillStyle(0x1a140d, 1);
    this.g.fillRect(0, 0, width, height);
    // Tall-window key light.
    this.g.fillStyle(0x2a2115, 0.6);
    this.g.fillRect(0, 0, width, seatY - 30);
    // Bench band.
    this.g.fillStyle(0x4a3320, 1);
    this.g.fillRect(0, seatY + 24, width, 26);
    this.g.fillStyle(0x3a2716, 1);
    this.g.fillRect(0, seatY + 50, width, 10);
    // Floor.
    this.g.fillStyle(0x241a10, 1);
    this.g.fillRect(0, height * 0.72, width, height * 0.28);

    this.title.setPosition(width / 2, 12);
    this.lecternRect.setPosition(lectern.x, lectern.y);
    this.boardLabel.setPosition(width / 2, board.y - 12);

    return { seatY, seatW, seatX, spriteH, lectern, board };
  }
}
