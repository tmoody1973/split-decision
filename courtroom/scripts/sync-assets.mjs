// Copies the repo's shared assets into courtroom/public so Vite can serve them. Run
// automatically before dev/build (see package.json predev/prebuild). The courtroom is a
// consumer of the same events.jsonl / sprite manifest that feed the scoreboard and
// producer — this script is the only bridge, and it copies, never edits.
import { cp, mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(here, "..", "..");
const publicDir = resolve(here, "..", "public");

async function copyEpisode(caseId, srcRel) {
  const src = resolve(repoRoot, srcRel);
  if (!existsSync(src)) {
    console.warn(`  skip ${caseId}: ${srcRel} not found`);
    return;
  }
  const destDir = resolve(publicDir, "episodes", caseId);
  await mkdir(destDir, { recursive: true });
  await cp(src, resolve(destDir, "events.jsonl"));
  console.log(`  episode ${caseId} <- ${srcRel}`);

  // The pre-rendered replay soundtrack (Producer output) — optional; the player falls
  // back to a silent TimerClock replay when absent (e.g. the smoke fixture).
  const audioSrc = resolve(dirname(resolve(repoRoot, srcRel)), "deliberation.mp3");
  if (existsSync(audioSrc)) {
    await cp(audioSrc, resolve(destDir, "deliberation.mp3"));
    console.log(`  episode ${caseId} <- deliberation.mp3`);
  }
}

async function caseLabel(caseId) {
  try {
    const record = JSON.parse(
      await readFile(resolve(repoRoot, "data", "cases", `${caseId}.json`), "utf8"),
    );
    return record.name ?? caseId;
  } catch {
    return caseId;
  }
}

async function main() {
  await mkdir(publicDir, { recursive: true });

  // Every deliberation in the repo is replayable: episodes with a produced
  // deliberation.mp3 get the audio master clock; the rest replay silently on
  // the timer clock with synthesized timing. Audio-bearing episodes list first.
  const episodeIds = (await readdir(resolve(repoRoot, "episodes"), { withFileTypes: true }))
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .filter((id) => existsSync(resolve(repoRoot, "episodes", id, "events.jsonl")))
    .sort();

  const entries = [];
  for (const id of episodeIds) {
    await copyEpisode(id, `episodes/${id}/events.jsonl`);
    const hasAudio = existsSync(resolve(repoRoot, "episodes", id, "deliberation.mp3"));
    const label = await caseLabel(id);
    entries.push({ id, label: hasAudio ? `${label} 🔊` : label, hasAudio });
  }
  entries.sort((a, b) => Number(b.hasAudio) - Number(a.hasAudio) || a.label.localeCompare(b.label));

  // The hand-written 10-event smoke fixture, served as its own "episode".
  await copyEpisode("smoke", "fixtures/smoke.jsonl");
  entries.push({ id: "smoke", label: "Smoke fixture (10 events)", hasAudio: false });

  // Sprite sheets + manifest (textualist & pragmatist exist today; the rest fall back
  // to coloured rectangles at runtime).
  const spritesSrc = resolve(repoRoot, "assets", "sprites");
  const spritesDest = resolve(publicDir, "assets", "sprites");
  if (existsSync(spritesSrc)) {
    await cp(spritesSrc, spritesDest, { recursive: true });
    console.log("  sprites <- assets/sprites");
  } else {
    console.warn("  skip sprites: assets/sprites not found");
  }

  // A manifest of which episodes are available, for the picker.
  const index = {
    default: entries.find((e) => e.hasAudio)?.id ?? entries[0].id,
    episodes: entries.map(({ id, label }) => ({ id, label })),
  };
  await writeFile(
    resolve(publicDir, "episodes", "index.json"),
    JSON.stringify(index, null, 2),
  );
  console.log("  wrote episodes/index.json");
}

main().then(() => console.log("sync-assets: done")).catch((err) => {
  console.error(err);
  process.exit(1);
});
