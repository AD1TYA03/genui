// Capture site screenshots with headless Chrome.
// Usage: node scripts/screenshots.mjs [baseUrl]   (run `npm run preview` first)
import { mkdir } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import { readdirSync } from "node:fs";
import puppeteer from "puppeteer-core";

const BASE = process.argv[2] ?? "http://localhost:4400";
const OUT = new URL("../screenshots/", import.meta.url).pathname;

function chromePath() {
  if (process.env.CHROME_PATH) return process.env.CHROME_PATH;
  const root = join(homedir(), ".cache/puppeteer/chrome");
  const dir = readdirSync(root).filter((d) => d.startsWith("mac_arm-")).sort().pop();
  return join(root, dir, "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing");
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const shots = [
  { name: "home", path: "/", wait: 3000, full: true },
  { name: "home-hero", path: "/", wait: 3500 },
  { name: "wander", path: "/wander", wait: 2500, full: true },
  { name: "wander-top", path: "/wander", wait: 3500 },
  { name: "playground", path: "/playground?example=analytics-dashboard", wait: 3000 },
  { name: "playground-error", path: "/playground?example=support-triage", wait: 2500, breakCode: true },
  { name: "not-found", path: "/nope", wait: 800 },
];

const widths = [
  { w: 1440, h: 900, label: "1440" },
  { w: 390, h: 844, label: "390", mobile: true },
];

const only = process.env.ONLY?.split(",");

await mkdir(OUT, { recursive: true });
const browser = await puppeteer.launch({
  executablePath: chromePath(),
  headless: true,
  args: ["--no-sandbox", "--hide-scrollbars", "--force-color-profile=srgb"],
});

for (const vp of widths) {
  for (const s of shots) {
    if (only && !only.includes(s.name)) continue;
    const page = await browser.newPage();
    await page.setViewport({ width: vp.w, height: vp.h, deviceScaleFactor: vp.mobile ? 2 : 1, isMobile: !!vp.mobile, hasTouch: !!vp.mobile });
    page.on("pageerror", (e) => console.error(`[${s.name}@${vp.label}] pageerror:`, e.message));
    page.on("console", (m) => m.type() === "error" && console.error(`[${s.name}@${vp.label}] console:`, m.text()));
    await page.goto(BASE + s.path, { waitUntil: "networkidle0" });
    if (s.finish) {
      await sleep(600);
      await page.evaluate(() => document.querySelector('button[aria-label="Skip to end"]')?.click());
    }
    if (s.breakCode) {
      await page.focus("textarea");
      await page.keyboard.down("End");
      await page.evaluate(() => {
        const ta = document.querySelector("textarea");
        const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set;
        setter.call(ta, ta.value.replace('urgent = Callout("error"', 'urgent = Callout("error"').replace("triage = Table(", "triage = Tabel("));
        ta.dispatchEvent(new Event("input", { bubbles: true }));
      });
    }
    await sleep(s.wait);
    if (s.full) {
      // Scroll through so whileInView animations fire, then back to top.
      await page.evaluate(async () => {
        for (let y = 0; y < document.body.scrollHeight; y += 400) {
          window.scrollTo(0, y);
          await new Promise((r) => setTimeout(r, 60));
        }
        window.scrollTo(0, 0);
      });
      await sleep(900);
    }
    const file = join(OUT, `${process.env.PREFIX ?? ""}${s.name}-${vp.label}.png`);
    await page.screenshot({ path: file, fullPage: !!s.full });
    console.log("saved", file);
    await page.close();
  }
}
await browser.close();
