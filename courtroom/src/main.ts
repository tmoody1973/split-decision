import Phaser from "phaser";
import { AudioClock, loadEpisodeAudio } from "./audioClock";
import { CourtScene } from "./CourtScene";
import { TimerClock } from "./clock";
import { parseManifest, setPieceFile, type SpriteManifest } from "./manifest";
import { normalizeEvents, parseJsonl } from "./normalize";
import { RecordPanel } from "./RecordPanel";
import { TimelinePlayer } from "./TimelinePlayer";

interface EpisodeIndex {
  default: string;
  episodes: { id: string; label: string }[];
}

const params = new URLSearchParams(location.search);
const recordMode = params.get("record") === "1";

async function fetchText(url: string): Promise<string> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`fetch ${url} -> ${res.status}`);
  return res.text();
}

async function loadIndex(): Promise<EpisodeIndex> {
  try {
    return JSON.parse(await fetchText("episodes/index.json")) as EpisodeIndex;
  } catch {
    return { default: "cl-cluster-10878534", episodes: [] };
  }
}

async function loadManifest(): Promise<{ manifest: SpriteManifest; bgFile: string | null }> {
  try {
    const raw = JSON.parse(await fetchText("assets/sprites/manifest.json"));
    return { manifest: parseManifest(raw), bgFile: setPieceFile(raw, "courtroom_bg") };
  } catch (err) {
    console.warn("no sprite manifest — all jurists render as placeholders", err);
    return { manifest: {}, bgFile: null };
  }
}

function fmtTime(ms: number): string {
  const s = Math.floor(ms / 1000);
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

async function boot(): Promise<void> {
  if (recordMode) document.body.classList.add("record");

  const index = await loadIndex();
  const episodeId = params.get("episode") ?? index.default;
  const [rawEvents, { manifest, bgFile }, audio] = await Promise.all([
    fetchText(`episodes/${episodeId}/events.jsonl`),
    loadManifest(),
    loadEpisodeAudio(episodeId),
  ]);

  const events = normalizeEvents(parseJsonl(rawEvents));
  // Audio is the master clock whenever the episode ships a pre-rendered replay track;
  // the wall-clock timer remains the fallback (e.g. the smoke fixture has no audio).
  const clock = audio ? new AudioClock(audio) : new TimerClock();
  if (!audio) console.warn(`no deliberation.mp3 for ${episodeId} — silent TimerClock replay`);
  const player = new TimelinePlayer(events, clock);

  const recordRoot = document.getElementById("record") as HTMLElement;
  const record = new RecordPanel(recordRoot, (ms) => player.seek(ms));

  // Controls.
  const playBtn = document.getElementById("play") as HTMLButtonElement;
  const seek = document.getElementById("seek") as HTMLInputElement;
  const timeEl = document.getElementById("time") as HTMLElement;
  const picker = document.getElementById("episode-picker") as HTMLSelectElement;
  let scrubbing = false;

  for (const ep of index.episodes) {
    const opt = document.createElement("option");
    opt.value = ep.id;
    opt.textContent = ep.label;
    if (ep.id === episodeId) opt.selected = true;
    picker.appendChild(opt);
  }
  picker.addEventListener("change", () => {
    params.set("episode", picker.value);
    location.search = params.toString();
  });

  playBtn.addEventListener("click", () => player.toggle());
  seek.addEventListener("input", () => {
    scrubbing = true;
    player.seek((Number(seek.value) / 1000) * player.duration);
  });
  seek.addEventListener("change", () => (scrubbing = false));

  const onFrame = (now: number, duration: number, playing: boolean): void => {
    playBtn.textContent = playing ? "❚❚" : "▶";
    timeEl.textContent = `${fmtTime(now)} / ${fmtTime(duration)}`;
    if (!scrubbing) seek.value = String(duration > 0 ? (now / duration) * 1000 : 0);
  };

  new Phaser.Game({
    type: Phaser.AUTO,
    parent: "game",
    backgroundColor: "#0f0d0a",
    pixelArt: true,
    scale: { mode: Phaser.Scale.RESIZE, autoCenter: Phaser.Scale.NO_CENTER },
    scene: new CourtScene({ manifest, bgFile, player, record, onFrame }),
  });

  if (recordMode) {
    // Give the scene a beat to build, then autoplay for screen capture.
    setTimeout(() => player.play(), 400);
  }

  wireArchModal();
}

// The judged architecture diagram (PixiJS, lazy chunk) behind a modal — the diagram
// wears the product's own pixel register and exports the submission PNG.
function wireArchModal(): void {
  const modal = document.getElementById("arch-modal") as HTMLDialogElement;
  const openBtn = document.getElementById("arch-open") as HTMLButtonElement;
  const closeBtn = document.getElementById("arch-close") as HTMLButtonElement;
  const dlBtn = document.getElementById("arch-download") as HTMLButtonElement;
  let diagram: import("./archDiagram").ArchDiagram | null = null;

  openBtn.addEventListener("click", async () => {
    modal.showModal();
    if (!diagram) {
      const { createArchDiagram } = await import("./archDiagram");
      diagram = await createArchDiagram(document.getElementById("arch-canvas") as HTMLElement);
    }
    diagram.open();
  });
  const close = (): void => {
    diagram?.close();
    if (modal.open) modal.close();
  };
  closeBtn.addEventListener("click", close);
  modal.addEventListener("close", () => diagram?.close());
  dlBtn.addEventListener("click", async () => {
    if (!diagram) return;
    const a = document.createElement("a");
    a.href = await diagram.exportPng();
    a.download = "split-decision-architecture.png";
    a.click();
  });
}

boot().catch((err) => {
  console.error(err);
  const root = document.getElementById("record");
  if (root) root.textContent = `Failed to load: ${err}`;
});
