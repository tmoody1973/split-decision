import Phaser from "phaser";
import { AudioClock, loadEpisodeAudio } from "./audioClock";
import { CourtScene } from "./CourtScene";
import { TimerClock } from "./clock";
import { parseManifest, setPieceFile, type SpriteManifest } from "./manifest";
import { loadPodcastTimeline } from "./podcastTimeline";
import { normalizeEvents, parseJsonl } from "./normalize";
import { RecordPanel } from "./RecordPanel";
import { TimelinePlayer } from "./TimelinePlayer";

interface EpisodeIndex {
  default: string;
  episodes: { id: string; label: string; group?: string }[];
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

async function loadManifest(): Promise<{
  manifest: SpriteManifest;
  bgFile: string | null;
  deskFile: string | null;
}> {
  try {
    const raw = JSON.parse(await fetchText("assets/sprites/manifest.json"));
    return {
      manifest: parseManifest(raw),
      bgFile: setPieceFile(raw, "courtroom_bg"),
      deskFile: setPieceFile(raw, "news_desk"),
    };
  } catch (err) {
    console.warn("no sprite manifest — all jurists render as placeholders", err);
    return { manifest: {}, bgFile: null, deskFile: null };
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
  const wantPodcast = params.get("mode") === "podcast";
  const [rawEvents, { manifest, bgFile, deskFile }, pod] = await Promise.all([
    fetchText(`episodes/${episodeId}/events.jsonl`),
    loadManifest(),
    loadPodcastTimeline(episodeId), // null when the episode has no produced podcast
  ]);
  const podcast = wantPodcast && pod !== null;
  if (wantPodcast && !podcast) console.warn(`no podcast data for ${episodeId} — courtroom mode`);

  // Master clock: podcast mode plays the mixed episode; courtroom mode the replay
  // track. The wall-clock timer remains the fallback (e.g. the smoke fixture).
  const audio = await loadEpisodeAudio(episodeId, podcast ? "episode.mp3" : "deliberation.mp3");
  const clock = audio ? new AudioClock(audio) : new TimerClock();
  if (!audio) console.warn(`no audio for ${episodeId} — silent TimerClock replay`);

  const events = podcast ? pod.merged : normalizeEvents(parseJsonl(rawEvents));
  const player = new TimelinePlayer(events, clock);
  wireModeToggle(episodeId, podcast, pod !== null);

  const recordRoot = document.getElementById("record") as HTMLElement;
  const record = new RecordPanel(recordRoot, (ms) => player.seek(ms));
  const exhibition = episodeId.startsWith("landmark-");
  if (exhibition) {
    const title = recordRoot.querySelector(".record-title") as HTMLElement;
    title.innerHTML = 'The Record <span class="exh-badge">EXHIBITION</span>';
  }

  // Controls.
  const playBtn = document.getElementById("play") as HTMLButtonElement;
  const seek = document.getElementById("seek") as HTMLInputElement;
  const timeEl = document.getElementById("time") as HTMLElement;
  const picker = document.getElementById("episode-picker") as HTMLSelectElement;
  let scrubbing = false;

  // Grouped picker: the section labels themselves teach which episodes are
  // benchmark science, which are filed predictions, and which are exhibition.
  const groups = new Map<string, HTMLElement>();
  for (const ep of index.episodes) {
    let parent: HTMLElement = picker;
    if (ep.group) {
      if (!groups.has(ep.group)) {
        const og = document.createElement("optgroup");
        og.label = ep.group;
        picker.appendChild(og);
        groups.set(ep.group, og);
      }
      parent = groups.get(ep.group)!;
    }
    const opt = document.createElement("option");
    opt.value = ep.id;
    opt.textContent = ep.label;
    if (ep.id === episodeId) opt.selected = true;
    parent.appendChild(opt);
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
    scene: new CourtScene({
      manifest,
      bgFile,
      player,
      record,
      onFrame,
      exhibition,
      ...(podcast
        ? { stateEvents: pod.stateEvents, sceneTime: pod.sceneTime, streamAt: pod.streamAt, deskFile }
        : {}),
    }),
  });

  if (recordMode) {
    // Give the scene a beat to build, then autoplay for screen capture.
    setTimeout(() => player.play(), 400);
  }

  wireArchModal();
}

// PODCAST/CHAMBER toggle — only for episodes with a produced podcast (cue sheet +
// episode.mp3). Swapping the `mode` param reloads into the other view.
function wireModeToggle(episodeId: string, inPodcast: boolean, available: boolean): void {
  if (!available) return;
  const link = document.createElement("a");
  link.id = "mode-toggle";
  link.textContent = inPodcast ? "◂ CHAMBER" : "PODCAST ▸";
  const next = new URLSearchParams(location.search);
  next.set("episode", episodeId);
  if (inPodcast) next.delete("mode");
  else next.set("mode", "podcast");
  link.href = `?${next.toString()}`;
  const picker = document.getElementById("episode-picker") as HTMLElement;
  picker.parentElement?.insertBefore(link, picker);
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

  // Deep link: ?arch=1 opens the diagram; ?arch=png replaces the page with the
  // raw 2x export (how docs/architecture.png is regenerated headlessly).
  const archParam = new URLSearchParams(location.search).get("arch");
  if (archParam === "png") {
    void (async () => {
      const { createArchDiagram } = await import("./archDiagram");
      const d = await createArchDiagram(document.createElement("div"));
      const img = document.createElement("img");
      img.id = "arch-export";
      img.src = await d.exportPng();
      img.style.cssText =
        "position:fixed;inset:0;width:100vw;height:100vh;object-fit:contain;background:#1a140d;z-index:9999";
      document.body.appendChild(img);
    })();
  } else if (archParam) {
    openBtn.click();
  }
}

boot().catch((err) => {
  console.error(err);
  const root = document.getElementById("record");
  if (root) root.textContent = `Failed to load: ${err}`;
});
