import Phaser from "phaser";

// Speech bubble with a typewriter reveal paced to the utterance's own duration, so the
// text finishes as the (eventual) audio finishes. Reveal is derived from the playhead,
// not a timer, so it stays correct through pause and seek.
//
// The bubble BODY and its TAIL are decoupled: the tail stays pointed at the speaker,
// but the body clamps to the canvas bounds — otherwise edge-seat speakers (Textualist,
// Minimalist) get half their bubble clipped offscreen.
const MAX_WIDTH = 320;
const WIDE_WIDTH = 460; // long utterances wrap wider so the bubble stays shorter
const WIDE_AT_CHARS = 260;
const PAD = 10;
const MARGIN = 8; // minimum gap between bubble body and canvas edges

export class Bubble {
  private readonly scene: Phaser.Scene;
  private readonly container: Phaser.GameObjects.Container;
  private readonly bg: Phaser.GameObjects.Graphics;
  private readonly text: Phaser.GameObjects.Text;
  private fullText = "";
  private startMs = 0;
  private durMs = 1;
  private active = false;
  private anchorY = 0;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
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
    const wrap = fullText.length > WIDE_AT_CHARS ? WIDE_WIDTH : MAX_WIDTH;
    this.text.setWordWrapWidth(
      Math.min(wrap, this.scene.scale.width - 2 * MARGIN) - PAD * 2,
    );
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

  /** Point the tail at (x, y) — the speaker's head. The body clamps to the canvas. */
  anchor(x: number, y: number): void {
    if (x !== this.container.x || y !== this.anchorY) {
      this.container.setPosition(x, y);
      this.anchorY = y;
      this.redraw();
    }
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
    const w = this.text.width + PAD * 2;
    const h = this.text.height + PAD * 2;

    // Local coords are relative to the anchor (the speaker's head, container origin).
    // Clamp the body's global rect inside the canvas: horizontally against both edges,
    // vertically against the top (a long bubble slides down over the scene rather than
    // clipping — it renders above everything at depth 100).
    const { width: canvasW } = this.scene.scale;
    const anchorX = this.container.x;
    const clampedCenter = Phaser.Math.Clamp(
      anchorX,
      MARGIN + w / 2,
      Math.max(MARGIN + w / 2, canvasW - MARGIN - w / 2),
    );
    const ox = clampedCenter - anchorX;
    const desiredTopGlobal = this.anchorY - h - 8;
    const oy = desiredTopGlobal < MARGIN ? MARGIN - desiredTopGlobal : 0;

    const left = ox - w / 2;
    const top = -h - 8 + oy;
    this.text.setPosition(left + PAD, top + PAD);
    this.bg.clear();
    this.bg.fillStyle(0xf4ecd8, 0.98);
    this.bg.lineStyle(2, 0x2e2820, 1);
    this.bg.fillRoundedRect(left, top, w, h, 8);
    this.bg.strokeRoundedRect(left, top, w, h, 8);
    // Tail: base stays on the body's bottom edge but its x follows the speaker, so a
    // clamped body still points at whoever is talking. Skip it once the body has slid
    // down past the anchor (nothing sensible to point at).
    if (top + h < 0) {
      const baseX = Phaser.Math.Clamp(0, left + 12, left + w - 12);
      this.bg.fillTriangle(baseX - 8, top + h, baseX + 8, top + h, 0, Math.min(top + h + 10, 0));
    }
  }
}
