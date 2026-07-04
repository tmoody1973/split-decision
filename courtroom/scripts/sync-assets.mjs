// Copies the repo's shared assets into courtroom/public so Vite can serve them. Run
// automatically before dev/build (see package.json predev/prebuild). The courtroom is a
// consumer of the same events.jsonl / sprite manifest that feed the scoreboard and
// producer — this script is the only bridge, and it copies, never edits.
import { cp, mkdir, readFile, writeFile } from "node:fs/promises";
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
}

async function main() {
  await mkdir(publicDir, { recursive: true });

  // The real 193-event deliberation.
  await copyEpisode(
    "cl-cluster-10878534",
    "episodes/cl-cluster-10878534/events.jsonl",
  );

  // The hand-written 10-event smoke fixture, served as its own "episode".
  await copyEpisode("smoke", "fixtures/smoke.jsonl");

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
    default: "cl-cluster-10878534",
    episodes: [
      { id: "cl-cluster-10878534", label: "Pung v. Isabella County (193 events)" },
      { id: "smoke", label: "Smoke fixture (10 events)" },
    ],
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
