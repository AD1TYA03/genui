// First-time-user walkthrough in headless Chrome. Prints PASS/FAIL per check.
// Usage: node scripts/dogfood.mjs [baseUrl]   (preview on port 4400)
import { readdirSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import puppeteer from "puppeteer-core";

const BASE = process.argv[2] ?? "http://localhost:4400";
const root = join(homedir(), ".cache/puppeteer/chrome");
const dir = readdirSync(root).filter((d) => d.startsWith("mac_arm-")).sort().pop();
const exe = join(root, dir, "chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const results = [];
const check = (name, ok, detail = "") => {
  results.push({ name, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? `  (${detail})` : ""}`);
};

const browser = await puppeteer.launch({ executablePath: exe, headless: true, args: ["--hide-scrollbars"] });
const ctx = browser.defaultBrowserContext();
await ctx.overridePermissions(BASE, ["clipboard-read", "clipboard-write", "clipboard-sanitized-write"]);
const consoleErrors = [];

async function open(path, vp = { width: 1440, height: 900 }) {
  const page = await browser.newPage();
  await page.setViewport(vp);
  page.on("pageerror", (e) => consoleErrors.push(`${path}: ${e.message}`));
  page.on("console", (m) => m.type() === "error" && consoleErrors.push(`${path}: ${m.text()}`));
  page.on("requestfailed", (r) => consoleErrors.push(`${path}: request failed ${r.url()}`));
  await page.goto(BASE + path, { waitUntil: "networkidle0" });
  return page;
}
const clickText = (page, sel, text) =>
  page.evaluate(
    (sel, text) => {
      const el = [...document.querySelectorAll(sel)].find((e) => e.textContent?.trim().includes(text));
      el?.click();
      return !!el;
    },
    sel,
    text,
  );

// ── Home ──
{
  const page = await open("/");
  check("home: title", (await page.title()).includes("genui"));
  check("home: single h1", (await page.$$eval("h1", (h) => h.length)) === 1);
  for (const cmd of ["pip install genui-py", "npm install genui-react"]) {
    await page.click(`button[aria-label="Copy ${cmd}"]`);
    await sleep(150);
    const clip = await page.evaluate(() => navigator.clipboard.readText());
    const label = await page.evaluate((c) => !!document.querySelector(`button[aria-label="Copied ${c}"]`), cmd);
    check(`home: copy "${cmd}"`, clip === cmd && label, `clipboard="${clip}"`);
  }
  await sleep(4000);
  const heroRendered = await page.evaluate(() => document.querySelector("figure")?.innerText.includes("Lisbon"));
  check("home: hero replay renders streaming UI", !!heroRendered);
  // nav
  for (const [label, path] of [["Gallery", "/gallery"], ["Playground", "/playground"], ["Wander", "/wander"]]) {
    await page.goto(BASE + "/", { waitUntil: "networkidle0" });
    await clickText(page, "header nav a", label);
    await sleep(500);
    check(`nav: ${label} -> ${path}`, new URL(page.url()).pathname === path);
  }
  await page.goto(BASE + "/", { waitUntil: "networkidle0" });
  const links = await page.$$eval("a[href^='http']", (as) => [...new Set(as.map((a) => a.href))]);
  check("home: external links found", links.length >= 4, links.join(" "));
  globalThis.externalLinks = links;
  // keyboard: first tab = skip link, focus ring visible
  await page.keyboard.press("Tab");
  const first = await page.evaluate(() => document.activeElement?.textContent?.trim());
  check("a11y: first Tab hits skip link", first === "Skip to content", first);
  const order = [];
  for (let i = 0; i < 9; i++) {
    await page.keyboard.press("Tab");
    order.push(
      await page.evaluate(() => {
        const a = document.activeElement;
        const cs = getComputedStyle(a);
        return `${a.tagName}:${(a.getAttribute("aria-label") || a.textContent || "").trim().slice(0, 24)}|${cs.outlineStyle !== "none" && cs.outlineWidth !== "0px"}`;
      }),
    );
  }
  check("a11y: tab order + focus rings", order.every((o) => o.endsWith("|true")), order.map((o) => o.split("|")[0]).join(" > "));
  await page.close();
}

// ── Gallery ──
{
  const page = await open("/gallery");
  const ids = await page.$$eval("nav[aria-label='Examples'] button", (b) => b.map((x) => x.textContent.trim()));
  check("gallery: 6 examples listed", ids.length === 6, ids.join(", "));
  for (const title of ids) {
    await clickText(page, "nav[aria-label='Examples'] button", title);
    await sleep(1500);
    const midChars = await page.evaluate(() => document.querySelector("section [class*=tabular-nums]")?.textContent);
    const playing = await page.evaluate(() => !!document.querySelector('button[aria-label="Skip to end"]:not([disabled])'));
    // speed 4x
    await clickText(page, '[role="radio"]', "4×");
    const speedOn = await page.evaluate(() => [...document.querySelectorAll('[role="radio"]')].find((b) => b.getAttribute("aria-checked") === "true")?.textContent);
    // skip to end
    await page.click('button[aria-label="Skip to end"]');
    await sleep(900);
    const done = await page.evaluate(() => {
      const t = document.querySelector("section [class*=tabular-nums]")?.textContent ?? "";
      const [a, b] = t.split("/").map((x) => x.replace(/\D/g, ""));
      return a === b && a.length > 0;
    });
    // view code
    await clickText(page, "button", "View OpenUI Lang");
    await sleep(200);
    const codeShown = await page.evaluate(() => document.querySelector("section pre")?.textContent?.startsWith("root = "));
    await clickText(page, "button", "View OpenUI Lang");
    // replay
    await clickText(page, "button", "Replay");
    await sleep(700);
    const restarted = await page.evaluate(() => !!document.querySelector('button[aria-label="Skip to end"]:not([disabled])'));
    await page.click('button[aria-label="Skip to end"]');
    await sleep(600);
    const errs = await page.evaluate(() => document.querySelector("section")?.innerText.includes("Render error"));
    check(
      `gallery: ${title}`,
      playing && speedOn === "4×" && done && codeShown && restarted && !errs,
      `mid=${midChars?.trim()} speed=${speedOn} done=${done} code=${codeShown} replay=${restarted}`,
    );
    await clickText(page, '[role="radio"]', "1×");
  }
  // click a button inside rendered UI -> toast
  await clickText(page, "nav[aria-label='Examples'] button", "Travel booking");
  await sleep(500);
  await page.click('button[aria-label="Skip to end"]');
  await sleep(1200);
  await clickText(page, "section button", "Cancel");
  await sleep(500);
  const toast = await page.evaluate(() => document.querySelector('[role="status"]')?.innerText);
  check("gallery: button in rendered UI shows toast", !!toast && toast.includes("Cancel"), toast?.replace(/\n/g, " | "));
  await clickText(page, "a", "Open in playground");
  await sleep(1500);
  check("gallery: open in playground", page.url().includes("/playground?example=travel-booking"));
  await page.close();
}

// ── Playground ──
let shareUrl = "";
{
  const page = await open("/playground");
  await sleep(1500);
  const status = () => page.evaluate(() => document.querySelector('[aria-live="polite"].rounded-full, span[aria-live="polite"]')?.textContent?.trim());
  check("playground: loads valid", (await status())?.startsWith("valid"), await status());
  const opts = await page.$$eval("select option", (o) => o.map((x) => x.value));
  let allValid = true;
  for (const v of opts.filter(Boolean)) {
    await page.select("select", v);
    await sleep(900);
    const s = await status();
    const rendered = await page.evaluate(() => document.querySelector(".genui-frame")?.innerText.length > 50);
    if (!s?.startsWith("valid") || !rendered) allValid = false;
  }
  check("playground: every example loads, renders and is valid", allValid, opts.join(","));
  // introduce an error
  const setCode = (fn) =>
    page.evaluate((fnSrc) => {
      const ta = document.querySelector("textarea");
      const next = new Function("s", `return (${fnSrc})(s)`)(ta.value);
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, "value").set.call(ta, next);
      ta.dispatchEvent(new Event("input", { bubbles: true }));
    }, fn.toString());
  await page.select("select", "support-triage");
  await sleep(600);
  await setCode((s) => s.replace("triage = Table(", "triage = Tabel("));
  await sleep(900);
  const errStatus = await status();
  const errPanel = await page.evaluate(() => document.querySelector('[role="alert"]')?.innerText ?? "");
  const errLine = await page.evaluate(() => document.querySelectorAll(".bg-red-500\\/10").length);
  check("playground: error detected + shown", errStatus?.includes("error") && errPanel.includes("Tabel") && errLine > 0, `${errStatus}; ${errPanel.split("\n")[0]}`);
  const selVal = await page.$eval("select", (s) => s.value);
  check("playground: picker shows Custom program after edit", selVal === "");
  await setCode((s) => s.replace("triage = Tabel(", "triage = Table("));
  await sleep(900);
  check("playground: error clears after fix", (await status())?.startsWith("valid"), await status());
  // custom edit + share
  await setCode((s) => s.replace('"Support Ticket Triage"', '"Dogfood Ünïcode ✓ Triage"'));
  await sleep(900);
  await clickText(page, "button", "Share");
  await sleep(200);
  shareUrl = await page.evaluate(() => navigator.clipboard.readText());
  check("playground: share copies #code= URL", /#code=/.test(shareUrl), shareUrl.slice(0, 70) + "…");
  const sb = await page.$eval('a[href*="stackblitz"]', (a) => a.href);
  check("playground: StackBlitz URL", sb === "https://stackblitz.com/github/AD1TYA03/genui/tree/main/site", sb);
  await page.close();
}
{
  const page = await open(shareUrl.replace(/^https?:\/\/[^/]+/, ""));
  await sleep(1500);
  const restored = await page.evaluate(() => document.querySelector("textarea")?.value.includes("Dogfood Ünïcode ✓ Triage"));
  const rendered = await page.evaluate(() => document.querySelector(".genui-frame")?.innerText.includes("Dogfood Ünïcode ✓ Triage"));
  check("playground: share link restores program in fresh page", restored && rendered);
  await page.close();
}

// ── 404 ──
{
  const page = await open("/definitely-not-here");
  const txt = await page.evaluate(() => document.body.innerText);
  check("404 page", txt.includes("404") && txt.includes("Back home"));
  await page.close();
}

// ── Mobile overflow / layout shift ──
for (const path of ["/", "/gallery", "/playground", "/wander", "/nope"]) {
  const page = await open(path, { width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });
  await page.evaluateOnNewDocument(() => {});
  await sleep(2500);
  const r = await page.evaluate(() => {
    const over = [...document.querySelectorAll("body *")].filter((el) => {
      const b = el.getBoundingClientRect();
      if (!b.width) return false;
      // ignore content inside horizontal scrollers
      for (let p = el.parentElement; p; p = p.parentElement) {
        const ox = getComputedStyle(p).overflowX;
        if (ox === "auto" || ox === "scroll" || ox === "hidden" || ox === "clip") return false;
      }
      return b.right > window.innerWidth + 1;
    });
    return { sw: document.documentElement.scrollWidth, iw: window.innerWidth, over: over.slice(0, 3).map((e) => e.tagName + "." + String(e.className).slice(0, 40)) };
  });
  check(`mobile 390: no horizontal overflow ${path}`, r.sw <= r.iw && r.over.length === 0, `${r.sw}/${r.iw} ${r.over.join(", ")}`);
  await page.close();
}
// CLS on home + gallery
for (const path of ["/", "/gallery"]) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });
  await page.evaluateOnNewDocument(() => {
    window.__cls = 0;
    new PerformanceObserver((l) => {
      for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value;
    }).observe({ type: "layout-shift", buffered: true });
  });
  await page.goto(BASE + path, { waitUntil: "networkidle0" });
  await sleep(3000);
  const cls = await page.evaluate(() => window.__cls);
  check(`CLS ${path} < 0.1`, cls < 0.1, cls.toFixed(3));
  await page.close();
}

check("no console errors / failed requests", consoleErrors.length === 0, consoleErrors.slice(0, 5).join(" || "));
await browser.close();
console.log(`\n${results.filter((r) => r.ok).length}/${results.length} passed`);
console.log("EXTERNAL", JSON.stringify(globalThis.externalLinks));
