// Rendu : node teaser/render.mjs [teaser|jourj] [--apercu]
//   --apercu : n'exporte qu'une image par seconde (contrôle qualité), pas de vidéo.
import { createRequire } from "module";
import { fileURLToPath } from "url";
import { spawn, execFileSync } from "child_process";
import fs from "fs";
import path from "path";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const DIR = path.dirname(fileURLToPath(import.meta.url));
const CONFIG = require(path.join(DIR, "config.js"));
const version = process.argv.find((a) => CONFIG.versions[a]) || CONFIG.version;
const apercu = process.argv.includes("--apercu");
const OUT = path.join(DIR, "out", version);
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
page.on("pageerror", (e) => { console.error("Erreur page :", e.message); process.exit(1); });
await page.goto("file://" + path.join(DIR, "index.html") + "?v=" + version);
await page.waitForFunction(() => window.ready && window.TOTAL_FRAMES);
await page.evaluate(() => window.ready);
const total = await page.evaluate(() => window.TOTAL_FRAMES);
const grab = async (f) => {
  const b64 = await page.evaluate((n) => { window.renderFrame(n); return document.getElementById("c").toDataURL("image/png"); }, f);
  return Buffer.from(b64.split(",")[1], "base64");
};

if (apercu) {
  const dir = path.join(OUT, "apercu"); fs.mkdirSync(dir, { recursive: true });
  const fps = CONFIG.fps, extra = (process.env.FRAMES || "").split(",").filter(Boolean).map(Number);
  const frames = [...Array.from({ length: Math.ceil(total / fps) }, (_, s) => s * fps), ...extra, total - 1];
  for (const f of frames) fs.writeFileSync(path.join(dir, `f${String(f).padStart(4, "0")}.png`), await grab(f));
  console.log(`Aperçu : ${frames.length} images dans ${dir}`);
  await browser.close(); process.exit(0);
}

const muet = path.join(OUT, `lsmx-bf-${version}-muet.mp4`);
const ff = spawn("ffmpeg", ["-y", "-v", "error", "-f", "image2pipe", "-c:v", "png", "-framerate", String(CONFIG.fps), "-i", "-",
  "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-r", String(CONFIG.fps),
  "-movflags", "+faststart", muet], { stdio: ["pipe", "inherit", "inherit"] });
const t0 = Date.now();
for (let f = 0; f < total; f++) {
  const buf = await grab(f);
  if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
  if (f === total - 1) fs.writeFileSync(path.join(OUT, "cover.png"), buf);
  if (f % 60 === 0) process.stdout.write(`\r  image ${f}/${total}  (${((Date.now() - t0) / 1000).toFixed(0)} s)`);
}
ff.stdin.end();
await new Promise((r) => ff.on("close", r));
await browser.close();
console.log(`\nVidéo muette : ${muet}`);

// bande son générée en code + mixage
const cfgJson = path.join(OUT, "config.json");
fs.writeFileSync(cfgJson, JSON.stringify({ ...CONFIG, rendu: version }));
const wav = path.join(OUT, "son.wav");
execFileSync("python3", [path.join(DIR, "son.py"), cfgJson, wav], { stdio: "inherit" });
const final = path.join(OUT, `lsmx-bf-${version}.mp4`);
execFileSync("ffmpeg", ["-y", "-v", "error", "-i", muet, "-i", wav, "-filter_complex", "[1:a]loudnorm=I=-14:TP=-1.5:LRA=11[a]",
  "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", final]);
console.log(`Vidéo avec son : ${final}\nMiniature : ${path.join(OUT, "cover.png")}`);
