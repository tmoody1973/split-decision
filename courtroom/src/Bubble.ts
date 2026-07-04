import Phaser from "phaser";

// Speech bubble with a typewriter reveal paced to the utterance's own duration, so the
// text finishes as the (eventual) audio finishes. Reveal is derived from the playhead,
// not a timer, so it stays correct through pause and seek.
const MAX_WIDTH = 320;
const PAD = 10;

export class Bubble {
  private readonly container: Phaser.GameObjects.Container;
  private readonly bg: Phaser.GameObjects.Graphics;
  private readonly text: Phaser.GameObjects.Text;
  private fullText = "";
  private startMs = 0;
  private durMs = 1;
  private active = false;

  constructor(scene: Phaser.Scene) {
    this.bg = scene.add.graphics();
    this.text = scene.add.text(0, 0, "", {
      fontFamily: "ui-sans-serif, system-ui, sans-serif",
      fontSize: "14px",
      color: "#1a1206",
      wordWrap: { width: MAX_WIDTH - PAD * 2 },
      lineSpacing: 2,
    });
    this.container = scene.add.container(0, 0, [this.bg, this.text]);
    this.container.setDepth(100).setVisible(false);
  }

  show(fullText: string, startMs: number, durMs: number): void {
    this.fullText = fullText;
    this.startMs = startMs;
    this.durMs = Math.max(1, durMs);
    this.active = true;
    this.container.setVisible(true);
  }

  hide(): void {
    this.active = false;
    this.container.setVisible(false);
  }

  get visible(): boolean {
    return this.active;
  }

  /** Position the bubble's bottom-center tail at (x, y). */
  anchor(x: number, y: number): void {
    this.container.setPosition(x, y);
  }

  update(nowMs: number): void {
    if (!this.active) return;
    const frac = Phaser.Math.Clamp((nowMs - this.startMs) / this.durMs, 0, 1);
    const shown = Math.floor(frac * this.fullText.length);
    const slice = this.fullText.slice(0, shown);
    if (slice !== this.text.text) {
      this.text.setText(slice);
      this.redraw();
    }
  }

  private redraw(): void {
    this.text.setPosition(-this.text.width / 2, -this.text.height - PAD - 8);
    const w = this.text.width + PAD * 2;
    const h = this.text.height + PAD * 2;
    const left = -w / 2;
    const top = -h - 8;
    this.bg.clear();
    this.bg.fillStyle(0xf4ecd8, 0.98);
    this.bg.lineStyle(2, 0x2e2820, 1);
    this.bg.fillRoundedRect(left, top, w, h, 8);
    this.bg.strokeRoundedRect(left, top, w, h, 8);
    // Tail.
    this.bg.fillTriangle(-8, top + h, 8, top + h, 0, top + h + 10);
  }
}
