import Phaser from "phaser";
import { Bubble } from "./Bubble";
import { JuristSprite } from "./JuristSprite";
import type { SpriteManifest } from "./manifest";
import { JURIST_ORDER, personaFor } from "./personas";
import { RecordPanel, tallyOf } from "./RecordPanel";
import { Stage } from "./Stage";
import { TimelinePlayer } from "./TimelinePlayer";
import { VoteBoard } from "./VoteBoard";
import type { Place } from "./types";

export interface SceneDeps {
  manifest: SpriteManifest;
  player: TimelinePlayer;
  record: RecordPanel;
  onFrame: (now: number, duration: number, playing: boolean) => void;
}

// The renderer proper. It reconstructs stage state from the player every frame and drives
// the visuals — no timeline logic of its own. Forward playback animates (walk, flip,
// typewriter, flash); a seek snaps everything to state instead.
export class CourtScene extends Phaser.Scene {
  private stage!: Stage;
  private board!: VoteBoard;
  private bubble!: Bubble;
  private sprites: Record<string, JuristSprite> = {};
  private verdictBanner!: Phaser.GameObjects.Text;
  private bubbleIndex = -1;

  constructor(private readonly deps: SceneDeps) {
    super("court");
  }

  preload(): void {
    this.load.on("loaderror", (file: Phaser.Loader.File) => {
      console.warn(`sprite sheet missing, falling back to placeholder: ${file.key}`);
    });
    for (const [id, entry] of Object.entries(this.deps.manifest)) {
      const cfg = { frameWidth: entry.frame_w, frameHeight: entry.frame_h };
      this.load.spritesheet(`${id}-idle`, `assets/sprites/${entry.sheets.idle}`, cfg);
      this.load.spritesheet(`${id}-walk`, `assets/sprites/${entry.sheets.walk}`, cfg);
    }
  }

  create(): void {
    for (const [id, entry] of Object.entries(this.deps.manifest)) {
      if (this.textures.exists(`${id}-idle`)) {
        this.anims.create({
          key: `${id}-idle`,
          frames: this.anims.generateFrameNumbers(`${id}-idle`, { frames: entry.anims.idle }),
          frameRate: entry.fps,
          repeat: -1,
        });
      }
      if (this.textures.exists(`${id}-walk`)) {
        this.anims.create({
          key: `${id}-walk`,
          frames: this.anims.generateFrameNumbers(`${id}-walk`, { frames: entry.anims.walk }),
          frameRate: entry.fps,
          repeat: -1,
        });
      }
    }

    this.stage = new Stage(this);
    this.board = new VoteBoard(this);
    this.bubble = new Bubble(this);

    const seatW = this.scale.width / JURIST_ORDER.length;
    for (const id of JURIST_ORDER) {
      this.sprites[id] = new JuristSprite(this, personaFor(id), this.deps.manifest[id], seatW);
    }

    this.verdictBanner = this.add
      .text(0, 0, "", {
        fontFamily: "ui-monospace, monospace",
        fontSize: "34px",
        color: "#f0d79a",
        fontStyle: "bold",
        backgroundColor: "#1a140dcc",
        padding: { x: 20, y: 12 },
      })
      .setOrigin(0.5)
      .setDepth(200)
      .setVisible(false);

    this.doLayout(this.scale.width, this.scale.height);
    this.scale.on("resize", (size: Phaser.Structs.Size) => this.doLayout(size.width, size.height));

    // Prime everything to t=0.
    this.applyState(0, true);
  }

  private doLayout(width: number, height: number): void {
    const layout = this.stage.layout(width, height);
    JURIST_ORDER.forEach((id, i) => {
      const s = this.sprites[id];
      s.setSeat(layout.seatX(i), layout.seatY);
      s.setLectern(layout.lectern.x, layout.lectern.y);
    });
    this.board.layout(layout.board.x, layout.board.y, layout.board.width);
    this.verdictBanner.setPosition(width / 2, height * 0.5);
  }

  update(_time: number, delta: number): void {
    const { now, crossed, seeked } = this.deps.player.tick();
    this.applyState(now, seeked, delta);

    for (const ev of crossed) {
      if (ev.type === "vote_change") {
        this.board.flip(ev.agent, ev.to);
        this.cameras.main.flash(180, 240, 215, 154, false);
      } else if (ev.type === "verdict") {
        this.cameras.main.shake(260, 0.004);
        this.showVerdict(`${ev.position.toUpperCase()}  ${ev.vote_split}`);
      }
      if (ev.type !== "vote") this.deps.record.append(ev);
    }

    if (seeked) {
      this.deps.record.rebuild(this.deps.player.allEvents, now);
      this.verdictBanner.setVisible(false);
    }

    this.deps.onFrame(now, this.deps.player.duration, this.deps.player.playing);
  }

  private applyState(now: number, seeked: boolean, delta = 0): void {
    const state = this.deps.player.stateAt(now);

    for (const id of JURIST_ORDER) {
      const s = this.sprites[id];
      const place: Place = state.positions[id] ?? "bench";
      if (seeked) s.snapTo(place);
      else s.walkTo(place);
      s.setSpeaking(state.currentSpeaker === id);
      s.update(delta, now);
    }

    this.board.setVotes(state.votes);
    const { affirm, reverse } = tallyOf(state.votes);
    this.deps.record.setTally(affirm, reverse);

    this.updateBubble(now);
  }

  private updateBubble(now: number): void {
    const utt = this.deps.player.activeUtterance(now);
    if (utt && (utt.type === "speak" || utt.type === "vote_change")) {
      const sprite = this.sprites[utt.agent];
      const text = utt.type === "speak" ? utt.text : utt.reason_text;
      if (this.bubbleIndex !== utt.index) {
        this.bubble.show(text, utt.t, utt.durMs);
        this.bubbleIndex = utt.index;
      }
      const a = sprite.bubbleAnchor;
      this.bubble.anchor(a.x, a.y);
      this.bubble.update(now);
    } else if (this.bubble.visible) {
      this.bubble.hide();
      this.bubbleIndex = -1;
    }
  }

  private showVerdict(text: string): void {
    this.verdictBanner.setText(`VERDICT\n${text}`).setVisible(true).setAlpha(0);
    this.tweens.add({ targets: this.verdictBanner, alpha: 1, duration: 400 });
  }
}
