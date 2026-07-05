// Demo-video screen captures (MOO-248). Records the built app (vite preview on
// :4173) at 1920x1080 with Playwright's recordVideo. Captures carry NO audio by
// design — the Hyperframes composition lays the original episode MP3s underneath,
// and the app's AudioClock guarantees the visuals were driven by those exact files.
import { chromium } from "playwright";
import { mkdir, rename } from "node:fs/promises";

const BASE = "http://localhost:4173";
const OUT = new URL("./captures/", import.meta.url).pathname;
const SIZE = { width: 1920, height: 1080 };

async function record(name, seconds, run) {
  const browser = await chromium.launch({
    args: ["--autoplay-policy=no-user-gesture-required"],
  });
  const ctx = await browser.newContext({
    viewport: SIZE,
    recordVideo: { dir: OUT, size: SIZE },
  });
  const page = await ctx.newPage();
  await run(page);
  await page.waitForTimeout(seconds * 1000);
  const video = page.video();
  await ctx.close();
  const path = await video.path();
  await rename(path, `${OUT}${name}.webm`);
  await browser.close();
  console.log(`  ${name}.webm (${seconds}s)`);
}

await mkdir(OUT, { recursive: true });

// 1. Pung podcast mode from 0:00 — covers Beat 1 (tape cold open in the courtroom)
//    and Beat 4 (desk -> tape hard cut around 1:50-2:40 of the episode).
await record("pung-podcast", 175, async (page) => {
  await page.goto(`${BASE}/courtroom.html?episode=cl-cluster-10878534&mode=podcast&record=1`);
  await page.waitForTimeout(1500); // scene build + autoplay kick-in
});

// 2. Plessy verdict with the EXHIBITION badge: seek to ~40s before the end of the
//    replay track, then let the verdict land. record=1 hides controls; the seek
//    input still exists and works.
await record("plessy-verdict", 55, async (page) => {
  await page.goto(`${BASE}/courtroom.html?episode=landmark-plessy&record=1`);
  await page.waitForTimeout(1500);
  await page.evaluate(() => {
    const seek = document.getElementById("seek");
    seek.value = "920"; // ~92% of the replay
    seek.dispatchEvent(new Event("input", { bubbles: true }));
  });
});

// 3. Landing tour: hero hold -> diagram (animated dots) -> agent grid -> prompt modal.
await record("landing-tour", 42, async (page) => {
  await page.goto(`${BASE}/index.html`);
  await page.waitForTimeout(4000); // hero hold
  await page.evaluate(() => document.getElementById("diagram-mount").scrollIntoView({ behavior: "smooth", block: "center" }));
  await page.waitForTimeout(9000); // watch the dots run
  await page.evaluate(() => document.getElementById("agents").scrollIntoView({ behavior: "smooth", block: "center" }));
  await page.waitForTimeout(4000);
  await page.evaluate(() => {
    const card = Array.from(document.querySelectorAll(".agent")).find((c) =>
      c.textContent.includes("Textualist"),
    );
    card.click();
  });
  await page.waitForTimeout(8000); // read the prompt
  await page.evaluate(() => document.getElementById("pm-close").click());
});

console.log("captures done");
