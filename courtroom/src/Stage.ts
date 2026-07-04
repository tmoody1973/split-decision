import Phaser from "phaser";

// Static set dressing + the responsive layout math the scene reuses. Purely presentational:
// wood-toned backdrop, a bench band, a lectern, and the anchor points every dynamic object
// (jurors, vote board) is positioned against. layout() is re-run on every resize.

export interface StageLayout {
  seatY: number;
  seatW: number;
  seatX: (i: number) => number;
  lectern: { x: number; y: number };
  board: { x: number; y: number; width: number };
}

const SEATS = 9;
const SIDE_PAD = 48;

export class Stage {
  private readonly g: Phaser.GameObjects.Graphics;
  private readonly title: Phaser.GameObjects.Text;
  private readonly lecternRect: Phaser.GameObjects.Rectangle;
  private readonly boardLabel: Phaser.GameObjects.Text;

  constructor(scene: Phaser.Scene) {
    this.g = scene.add.graphics().setDepth(-10);
    this.title = scene.add
      .text(0, 12, "SPLIT DECISION — THE CHAMBER", {
        fontFamily: "ui-monospace, monospace",
        fontSize: "13px",
        color: "#9a8f7d",
        fontStyle: "bold",
      })
      .setOrigin(0.5, 0)
      .setDepth(5);
    this.lecternRect = scene.add.rectangle(0, 0, 90, 70, 0x5b3d22, 1).setDepth(-5);
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
    const seatY = Math.max(150, height * 0.34);
    const usable = width - SIDE_PAD * 2;
    const seatW = usable / SEATS;
    const seatX = (i: number) => SIDE_PAD + seatW / 2 + i * seatW;
    const lectern = { x: width / 2, y: height * 0.6 };
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

    return { seatY, seatW, seatX, lectern, board };
  }
}
