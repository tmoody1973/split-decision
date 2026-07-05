import Phaser from "phaser";
import { Bubble } from "./Bubble";
import { JuristSprite } from "./JuristSprite";
import type { SpriteManifest } from "./manifest";
import { JURIST_ORDER, personaFor } from "./personas";
import { RecordPanel, tallyOf } from "./RecordPanel";
import { replayState } from "./replayState";
import { Stage } from "./Stage";
import { TimelinePlayer } from "./TimelinePlayer";
import { VoteBoard } from "./VoteBoard";
import type { NormalizedEvent, Place } from "./types";

export interface SceneDeps {
  manifest: SpriteManifest;
  bgFile: string | null;
  player: TimelinePlayer;
  record: RecordPanel;
  onFrame: (now: number, duration: number, playing: boolean) => void;
  // Podcast mode (all optional; absent = plain courtroom replay):
  /** Full deliberation on the replay clock — the vote board's state source. */
  stateEvents?: NormalizedEvent[];
  /** Podcast clock -> replay clock (which deliberation moment the tape came from). */
  sceneTime?: (t: number) => number;
  /** Which set the camera shows at a podcast instant. */
  streamAt?: (t: number) => "studio" | "deliberation";
  /** News-desk set piece file; enables the studio set. */
  deskFile?: string | null;
  /** Landmark specials: exhibition label in the scene (contamination guard, visible). */
  exhibition?: boolean;
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
  // Studio set (podcast mode): a full-canvas cutaway above the courtroom.
  private studio?: {
    backdrop: Phaser.GameObjects.Graphics;
    deskBack: Phaser.GameObjects.Image; // chairs — behind the anchors
    desk: Phaser.GameObjects.Image; // counter — in front of them
    caption: Phaser.GameObjects.Text;
    anchors: Record<string, JuristSprite>;
  };
  private onStudio = false;

  constructor(private readonly deps: SceneDeps) {
    super("court");
  }

  preload(): void {
    this.load.on("loaderror", (file: Phaser.Loader.File) => {
      console.warn(`sprite sheet missing, falling back to placeholder: ${file.key}`);
    });
    if (this.deps.bgFile) {
      this.load.image("courtroom_bg", `assets/sprites/${this.deps.bgFile}`);
    }
    if (this.deps.deskFile) {
      this.load.image("news_desk", `assets/sprites/${this.deps.deskFile}`);
    }
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

    this.stage = new Stage(
      this,
      this.deps.exhibition
        ? "SPLIT DECISION — SPECIAL SESSION · EXHIBITION, NOT BENCHMARK"
        : undefined,
    );
    this.board = new VoteBoard(this);
    this.bubble = new Bubble(this);

    const seatW = this.scale.width / JURIST_ORDER.length;
    for (const id of JURIST_ORDER) {
      this.sprites[id] = new JuristSprite(this, personaFor(id), this.deps.manifest[id], seatW);
    }

    if (this.deps.deskFile && this.textures.exists("news_desk")) {
      const anchors: Record<string, JuristSprite> = {};
      const seatW = this.scale.width / 6;
      for (const id of ["anchor_lead", "anchor_analyst"]) {
        const a = new JuristSprite(this, personaFor(id), this.deps.manifest[id], seatW);
        a.setBaseDepth(305);
        a.disablePlate();
        a.setVisible(false);
        anchors[id] = a;
      }
      this.studio = {
        backdrop: this.add.graphics().setDepth(300).setVisible(false),
        deskBack: this.add.image(0, 0, "news_desk").setOrigin(0.5, 1).setDepth(302).setVisible(false),
        desk: this.add.image(0, 0, "news_desk").setOrigin(0.5, 1).setDepth(310).setVisible(false),
        caption: this.add
          .text(0, 0, "SPLIT DECISION — THE DESK", {
            fontFamily: "ui-monospace, monospace",
            fontSize: "13px",
            color: "#9a8f7d",
            fontStyle: "bold",
          })
          .setOrigin(0.5, 0)
          .setDepth(315)
          .setVisible(false),
        anchors,
      };
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
      s.setDisplayHeight(layout.spriteH);
      s.setSeat(layout.seatX(i), layout.seatY);
      s.setLectern(layout.lectern.x, layout.lectern.y);
    });
    this.board.layout(layout.board.x, layout.board.y, layout.board.width);
    this.verdictBanner.setPosition(width / 2, height * 0.5);

    if (this.studio) {
      const s = this.studio;
      s.backdrop.clear();
      s.backdrop.fillStyle(0x10131f, 1).fillRect(0, 0, width, height);
      s.backdrop.fillStyle(0x1c2233, 1).fillRect(0, height * 0.7, width, height * 0.3);
      // Spotlight wash behind the desk.
      s.backdrop.fillStyle(0x2a3350, 0.5).fillRect(width * 0.2, 0, width * 0.6, height * 0.7);
      // Frontal desk, split into two layers so the anchors sandwich between them:
      // the painted chairs render behind the sprites, the counter in front — the
      // same occlusion trick as the courtroom bench overlay.
      // Split at the desk's BACK edge (top of the surface band): everything from the
      // back edge down — the whole surface + front rail — renders in front of the
      // anchors, so a torso cropped below that line is swallowed by the desk.
      const SPLIT = 0.46;
      const deskW = Math.min(width * 0.62, 720);
      const scale = deskW / s.desk.width;
      for (const img of [s.deskBack, s.desk]) {
        img.setScale(scale).setPosition(width / 2, height * 0.86);
      }
      const texH = s.desk.height;
      s.deskBack.setCrop(0, 0, s.desk.width, texH * SPLIT);
      s.desk.setCrop(0, texH * SPLIT, s.desk.width, texH * (1 - SPLIT));
      const deskH = s.desk.displayHeight;
      const deskTop = height * 0.86 - deskH;
      // Seated read: torso crop line tucked just below the back edge, under the
      // front layer — the body meets the desk exactly where a seated person would.
      const CROP = 0.6;
      const anchorH = deskH * 0.72;
      const hiddenLine = deskTop + deskH * (SPLIT + 0.04);
      const baseline = hiddenLine + anchorH * (1 - CROP);
      const lead = s.anchors["anchor_lead"];
      const analyst = s.anchors["anchor_analyst"];
      for (const a of [lead, analyst]) {
        a.setDisplayHeight(anchorH);
        a.setCropBottom(CROP);
      }
      lead.setSeat(width / 2 - deskW * 0.2, baseline);
      analyst.setSeat(width / 2 + deskW * 0.2, baseline);
      s.caption.setPosition(width / 2, 12);
    }
  }

  private setStudioVisible(on: boolean): void {
    if (!this.studio || on === this.onStudio) return;
    this.onStudio = on;
    const s = this.studio;
    s.backdrop.setVisible(on);
    s.deskBack.setVisible(on);
    s.desk.setVisible(on);
    s.caption.setVisible(on);
    for (const a of Object.values(s.anchors)) a.setVisible(on);
    // A cut in either direction retires whichever bubble was up.
    this.bubble.hide();
    this.bubbleIndex = -1;
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
    this.setStudioVisible(this.deps.streamAt?.(now) === "studio");
    // In podcast mode the vote board reflects the deliberation moment the tape came
    // from (replay clock), reconstructed over the FULL event log — including votes
    // that never aired.
    const sceneT = this.deps.sceneTime ? this.deps.sceneTime(now) : now;
    const state = this.deps.stateEvents
      ? replayState(this.deps.stateEvents, sceneT)
      : this.deps.player.stateAt(now);

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

    if (this.studio) {
      for (const a of Object.values(this.studio.anchors)) {
        a.setSpeaking(false);
        a.update(delta, now);
      }
    }
    this.updateBubble(now);
  }

  private updateBubble(now: number): void {
    const utt = this.deps.player.activeUtterance(now);
    const sprite =
      utt?.type === "studio"
        ? this.studio?.anchors[utt.agent]
        : utt && (utt.type === "speak" || utt.type === "vote_change")
          ? this.sprites[utt.agent]
          : undefined;
    if (utt && sprite && (utt.type === "speak" || utt.type === "vote_change" || utt.type === "studio")) {
      const text = utt.type === "vote_change" ? utt.reason_text : utt.text;
      if (this.bubbleIndex !== utt.index) {
        this.bubble.show(text, utt.t, utt.durMs);
        this.bubbleIndex = utt.index;
      }
      sprite.setSpeaking(true);
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
