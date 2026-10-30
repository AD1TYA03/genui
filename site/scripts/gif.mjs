// Record the travel-booking gallery replay as frames, then assemble demo.gif with ffmpeg.
// Usage: node scripts/gif.mjs [baseUrl]   (run `npm run preview -- --port 4400` first)
import { execFileSync } from "node:child_process";
import { mkdirSync, readdirSync, rmSync, writeFileSync, statSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";
import puppeteer from "puppeteer-core";

const BASE = process.argv[2] ?? "http://localhost:4400";
const OUT = new URL("../public/demo.gif", import.meta.url).pathname;
const FR = join(tmpdir(), "genui-gif-frames");
rmSync(FR, { recursive: true, force: true });
mkdirSync(FR, { recursive: true });

const root = join(homedir(), ".cache/puppeteer/chrome");
const dir = readdirSync(root).filter((d) => d.startsWith("mac_arm-")).sort().pop();
const exe = join(root, dir, "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await puppeteer.launch({ executablePath: exe, headless: true, args: ["--hide-scrollbars", "--force-color-profile=srgb"] });
const page = await browser.newPage();
await page.setViewport({ width: 1280, height: 820, deviceScaleFactor: 1 });
await page.goto(`${BASE}/gallery?example=travel-booking`, { waitUntil: "networkidle0" });
// Restart at 2x so the whole response lands in ~8s.
await page.evaluate(() => {
  [...document.querySelectorAll('[role="radio"]')].find((b) => b.textContent?.trim() === "2×")?.click();
  document.querySelector('button[aria-label="Restart"]')?.click();
});
await page.evaluate(() => {
  document.querySelector("header").style.display = "none";
  document.querySelector("footer").style.display = "none";
  document.querySelector("main").style.minHeight = "3000px";
});
const stageTop = await page.evaluate(() => {
  const s = document.querySelector("section[aria-label]");
  return s.getBoundingClientRect().top + window.scrollY - 16;
});
const box = await page.evaluate(() => {
  const r = document.querySelector("section[aria-label]").getBoundingClientRect();
  return { x: Math.round(r.left) - 16, w: Math.round(r.width) + 32 };
});
await page.evaluate((y) => window.scrollTo(0, y), stageTop);

const frames = [];
const start = Date.now();
let doneAt = null;
while (true) {
  const t = Date.now() - start;
  const state = await page.evaluate((top) => {
    const s = document.querySelector("section[aria-label]");
    const card = s.firstElementChild.getBoundingClientRect();
    const bottom = card.bottom + window.scrollY;
    const target = Math.max(top, bottom - window.innerHeight + 24);
    window.scrollTo(0, window.scrollY + (target - window.scrollY) * 0.35);
    return { done: !!document.querySelector('button[aria-label="Skip to end"][disabled]'), y: Math.round(window.scrollY) };
  }, stageTop);
  const f = join(FR, `f${String(frames.length).padStart(4, "0")}.png`);
  await page.screenshot({ path: f, clip: { x: box.x, y: state.y, width: box.w, height: 820 } });
  frames.push({ f, t });
  if (state.done && doneAt == null) doneAt = t;
  if (doneAt != null && t - doneAt > 2200) break;
  if (t > 20000) break;
  await sleep(40);
}
await browser.close();

// Resample to a constant 10 fps by duration.
let list = "";
for (let i = 0; i < frames.length; i++) {
  const d = ((frames[i + 1]?.t ?? frames[i].t + 100) - frames[i].t) / 1000;
  list += `file '${frames[i].f}'\nduration ${d.toFixed(3)}\n`;
}
list += `file '${frames.at(-1).f}'\n`;
writeFileSync(join(FR, "list.txt"), list);
const vf = "fps=10,scale=900:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle";
execFileSync("ffmpeg", ["-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", join(FR, "list.txt"), "-vf", vf, "-loop", "0", OUT]);
console.log(`frames=${frames.length} duration=${(frames.at(-1).t / 1000).toFixed(1)}s size=${(statSync(OUT).size / 1048576).toFixed(2)}MB -> ${OUT}`);
