import { Application, Container, Graphics, Text } from "pixi.js";

// The judged architecture diagram, rendered in the product's own pixel register
// (PixiJS; hard edges, no antialiasing, THEME.md palette). Lazy-loaded behind the
// ARCHITECTURE modal so Phaser's bundle stays untouched. Also exports the PNG used
// in the README / Devpost submission — one artifact, two homes.

const W = 1280;
const H = 720;

const C = {
  bg: 0x1a140d,
  panel: 0x241a10,
  wood: 0x4a3320,
  woodEdge: 0x8a5a2b,
  parchment: 0xf4ecd8,
  ink: 0x1a1206,
  navy: 0x1e2a4a,
  navyHi: 0x3a5a9a,
  burgundy: 0x7a1f2b,
  gold: 0xf0d79a,
  dim: 0x9a8f7d,
  green: 0x3f6d4e,
};

interface Node {
  id: string;
  x: number; y: number; w: number; h: number;
  title: string;
  lines: string[];
  badge?: string;       // model id chip
  badgeColor?: number;
  accent?: number;
}

const NODES: Node[] = [
  { id: "sources", x: 24, y: 150, w: 190, h: 170, title: "CASE DATA", accent: C.green,
    lines: ["CourtListener v4", "Oyez plain-English", "SCDB ground truth", "", "post-2025-06 only", "(contamination guard)"] },
  { id: "clerk", x: 262, y: 176, w: 172, h: 118, title: "CLERK", accent: C.burgundy,
    lines: ["case record ->", "bench memo"], badge: "qwen3.7-max", badgeColor: C.burgundy },
  { id: "chamber", x: 482, y: 96, w: 236, h: 278, title: "DELIBERATION CHAMBER", accent: C.navyHi,
    lines: ["9 jurists, 5 rounds", "private votes first,", "debate second —", "flips are measured", "persuasion; fallbacks", "flagged, never silent"],
    badge: "9 x qwen3.7-plus", badgeColor: C.navy },
  { id: "events", x: 766, y: 150, w: 176, h: 170, title: "events.jsonl", accent: C.gold,
    lines: ["THE SPINE", "", "one immutable log,", "every consumer", "reads the same", "record verbatim"] },
  { id: "scoreboard", x: 990, y: 44, w: 266, h: 122, title: "SCOREBOARD", accent: C.green,
    lines: ["paired on the same 24:", "solo 75% · jury 66.7%", "debate 66.7% · base 75%", "neutral control 66.7%", "an honest null, published"] },
  { id: "producer", x: 990, y: 196, w: 266, h: 150, title: "PRODUCER", accent: C.burgundy,
    lines: ["clips -> two-way script", "verbatim tape only", "ffmpeg mix -> MP3"],
    badge: "qwen3-tts-vd · wan2.6-t2i", badgeColor: C.navy },
  { id: "courtroom", x: 990, y: 376, w: 266, h: 122, title: "PIXEL COURTROOM", accent: C.navyHi,
    lines: ["Phaser replay VCR", "audio drives visuals", "(this app)"] },
  { id: "oss", x: 800, y: 540, w: 230, h: 130, title: "OSS BUCKET", accent: C.gold,
    lines: ["podcast MP3 +", "RSS feed", "episode art"] },
  { id: "sas", x: 320, y: 540, w: 220, h: 130, title: "SAS RUNNER", accent: C.green,
    lines: ["nginx: this app", "run_episode.py", "(systemd pipeline)"] },
  { id: "livebench", x: 560, y: 540, w: 220, h: 130, title: "LIVE BENCH", accent: C.burgundy,
    lines: ["judges convene a", "REAL deliberation,", "streamed as it runs"] },
];

// Elbow-routed edges as waypoint polylines; dots animate along them.
const EDGES: [string, number[][]][] = [
  ["sources->clerk", [[214, 235], [262, 235]]],
  ["clerk->chamber", [[434, 235], [482, 235]]],
  ["chamber->events", [[718, 235], [766, 235]]],
  ["events->scoreboard", [[942, 200], [966, 200], [966, 105], [990, 105]]],
  ["events->producer", [[942, 250], [966, 250], [966, 271], [990, 271]]],
  ["events->courtroom", [[942, 300], [966, 300], [966, 437], [990, 437]]],
  ["producer->oss", [[1123, 346], [1123, 470], [880, 470], [880, 540]]],
  ["sas->chamber", [[460, 540], [460, 420], [530, 420], [530, 374]]],
  ["oss->courtroom", [[1030, 605], [1200, 605], [1200, 498]]],
];

function drawPixelBox(g: Graphics, n: Node): void {
  g.rect(n.x + 4, n.y + 6, n.w, n.h).fill({ color: 0x000000, alpha: 0.45 }); // hard shadow
  g.rect(n.x, n.y, n.w, n.h).fill(C.panel).stroke({ width: 3, color: n.accent ?? C.woodEdge });
  g.rect(n.x, n.y, n.w, 26).fill(n.accent ?? C.wood);
}

export interface ArchDiagram {
  open(): void;
  close(): void;
  exportPng(): Promise<string>;
}

export async function createArchDiagram(mount: HTMLElement): Promise<ArchDiagram> {
  const app = new Application();
  await app.init({
    width: W, height: H,
    background: C.bg,
    antialias: false,
    autoStart: false,
    resolution: 2, // 2x export for the submission PNG; CSS caps on-screen size
    autoDensity: true,
  });
  // Fit the whole diagram on screen: constrain BOTH axes and let the browser keep
  // the canvas's intrinsic 16:9 — a width-only rule overflows short windows and
  // <dialog> doesn't scroll, clipping the bottom of the diagram.
  app.canvas.style.maxWidth = "min(1280px, 92vw)";
  app.canvas.style.maxHeight = "calc(92vh - 60px)";
  app.canvas.style.width = "auto";
  app.canvas.style.height = "auto";
  app.canvas.style.imageRendering = "pixelated";
  mount.appendChild(app.canvas);

  const root = new Container();
  app.stage.addChild(root);

  const mono = "ui-monospace, Menlo, monospace";

  // Qwen Cloud region: everything model-shaped lives inside the dashed frame.
  const region = new Graphics();
  const rx = 244, ry = 60, rw = 716, rh = 330;
  for (let x = rx; x < rx + rw; x += 16) region.rect(x, ry, 8, 3).fill(C.woodEdge);
  for (let x = rx; x < rx + rw; x += 16) region.rect(x, ry + rh, 8, 3).fill(C.woodEdge);
  for (let y = ry; y < ry + rh; y += 16) region.rect(rx, y, 3, 8).fill(C.woodEdge);
  for (let y = ry; y < ry + rh; y += 16) region.rect(rx + rw, y, 3, 8).fill(C.woodEdge);
  root.addChild(region);
  root.addChild(new Text({
    text: "QWEN CLOUD (Singapore)",
    style: { fontFamily: mono, fontSize: 13, fill: C.gold, fontWeight: "bold" },
    x: rx + 12, y: ry + 8,
  }));

  const cloudBand = new Graphics();
  cloudBand.rect(300, 516, 748, 178).stroke({ width: 3, color: C.wood });
  root.addChild(cloudBand);
  root.addChild(new Text({
    text: "ALIBABA CLOUD — DEPLOYED",
    style: { fontFamily: mono, fontSize: 12, fill: C.dim, fontWeight: "bold" },
    x: 308, y: 520,
  }));

  // Edges under nodes.
  const edges = new Graphics();
  for (const [, pts] of EDGES) {
    edges.moveTo(pts[0][0], pts[0][1]);
    for (const p of pts.slice(1)) edges.lineTo(p[0], p[1]);
    edges.stroke({ width: 3, color: C.woodEdge, alpha: 0.9 });
    const [ex, ey] = pts[pts.length - 1];
    const [px, py] = pts[pts.length - 2];
    const dx = Math.sign(ex - px), dy = Math.sign(ey - py);
    if (dx !== 0) edges.poly([ex, ey, ex - dx * 10, ey - 6, ex - dx * 10, ey + 6], true).fill(C.woodEdge);
    else edges.poly([ex, ey, ex - 6, ey - dy * 10, ex + 6, ey - dy * 10], true).fill(C.woodEdge);
  }
  root.addChild(edges);

  // Nodes.
  const boxes = new Graphics();
  for (const n of NODES) drawPixelBox(boxes, n);
  root.addChild(boxes);
  for (const n of NODES) {
    const lightHeader = n.accent === C.gold || n.accent === C.parchment;
    root.addChild(new Text({
      text: n.title,
      style: { fontFamily: mono, fontSize: 13, fill: lightHeader ? C.ink : C.parchment, fontWeight: "bold" },
      x: n.x + 10, y: n.y + 5,
    }));
    root.addChild(new Text({
      text: n.lines.join("\n"),
      style: { fontFamily: mono, fontSize: 11.5, fill: C.dim, lineHeight: 16 },
      x: n.x + 10, y: n.y + 34,
    }));
    if (n.badge) {
      const bw = n.badge.length * 7 + 14;
      const chip = new Graphics()
        .rect(n.x + 8, n.y + n.h - 24, bw, 17)
        .fill(n.badgeColor ?? C.navy)
        .stroke({ width: 2, color: C.gold });
      root.addChild(chip);
      root.addChild(new Text({
        text: n.badge,
        style: { fontFamily: mono, fontSize: 10, fill: C.gold },
        x: n.x + 14, y: n.y + n.h - 21,
      }));
    }
  }

  // Nine jurist pixels on the chamber + one foreperson.
  const juristAccents = [0x7a1f2b, 0x5b4a2f, 0x3f6d4e, 0xc27b2c, 0x6b5b8a, 0x8a5a2b, 0x3a5a9a, 0x555f66, 0x9a8f7d];
  const chamber = NODES.find((n) => n.id === "chamber")!;
  const pix = new Graphics();
  juristAccents.forEach((color, i) => {
    const jx = chamber.x + 22 + i * 22;
    const jy = chamber.y + chamber.h - 42;
    pix.rect(jx, jy, 14, 20).fill(C.navy).stroke({ width: 2, color });
    pix.rect(jx + 3, jy - 8, 8, 8).fill(color);
  });
  pix.rect(chamber.x + chamber.w - 40, chamber.y + chamber.h - 116, 16, 24)
    .fill(C.burgundy).stroke({ width: 2, color: C.gold });
  root.addChild(pix);
  root.addChild(new Text({
    text: "foreperson · qwen3.7-max",
    style: { fontFamily: mono, fontSize: 9, fill: C.dim },
    x: chamber.x + 22, y: chamber.y + chamber.h - 104,
  }));

  root.addChild(new Text({
    text: "SPLIT DECISION — SYSTEM ARCHITECTURE",
    style: { fontFamily: mono, fontSize: 20, fill: C.gold, fontWeight: "bold" },
    x: 24, y: 16,
  }));
  root.addChild(new Text({
    text: "two agent societies, one event log: a chamber that deliberates, a newsroom that covers it",
    style: { fontFamily: mono, fontSize: 12, fill: C.dim },
    x: 24, y: 44,
  }));
  root.addChild(new Text({
    text: "tape integrity:\npodcast, scoreboard and\ncourtroom read the same\nevents.jsonl — juror words\nare never rewritten",
    style: { fontFamily: mono, fontSize: 11, fill: C.dim, lineHeight: 16 },
    x: 24, y: H - 130,
  }));

  // Animated packets: one dot per edge, phase-offset, resampled along the polyline.
  const dots = EDGES.map(([, pts], i) => {
    const dot = new Graphics().rect(-4, -4, 8, 8).fill(C.gold);
    dot.position.set(pts[0][0], pts[0][1]);
    root.addChild(dot);
    const segs: { x: number; y: number; len: number }[] = [];
    let total = 0;
    for (let k = 1; k < pts.length; k++) {
      const len = Math.hypot(pts[k][0] - pts[k - 1][0], pts[k][1] - pts[k - 1][1]);
      segs.push({ x: pts[k - 1][0], y: pts[k - 1][1], len });
      total += len;
    }
    return { dot, pts, segs, total, phase: i / EDGES.length };
  });
  let t = 0;
  app.ticker.add((ticker) => {
    t += ticker.deltaMS / 2400;
    for (const d of dots) {
      let dist = ((t + d.phase) % 1) * d.total;
      for (let k = 0; k < d.segs.length; k++) {
        const s = d.segs[k];
        if (dist <= s.len || k === d.segs.length - 1) {
          const frac = s.len === 0 ? 0 : Math.min(1, dist / s.len);
          const nx = d.pts[k + 1][0], ny = d.pts[k + 1][1];
          d.dot.position.set(s.x + (nx - s.x) * frac, s.y + (ny - s.y) * frac);
          break;
        }
        dist -= s.len;
      }
    }
  });

  return {
    open(): void { app.start(); },
    close(): void { app.stop(); },
    async exportPng(): Promise<string> {
      app.render();
      return app.renderer.extract.base64(app.stage);
    },
  };
}
