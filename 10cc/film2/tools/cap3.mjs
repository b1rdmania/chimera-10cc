// The full merged wall on the virtual clock.
//   node cap3.mjs stills <outdir> <t,t,...> [dpr=2]       -> outdir/f-<t>.jpg (1 s of pre-roll before each)
//   node cap3.mjs video <t0> <t1> <out.mp4> [dpr=2]        -> a silent 1920x1080 segment, frame i = song time t0 + i/30
// Per frame: __replayFull(t) sets telemetry and layout, two native animation frames let layout and
// ResizeObserver settle (a resized canvas is cleared), then one 1/30 s virtual step draws every screen.
import { launch, VCLOCK } from "../../capture/lib.mjs";
import { spawn } from "node:child_process";
import fs from "node:fs";
const [MODE, ...rest] = process.argv.slice(2);
const FPS = 30;
const dpr = +(MODE === "stills" ? rest[2] ?? 2 : rest[3] ?? 2);
const b = await launch(true);
const p = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: dpr });
await p.addInitScript(`window.__nativeRAF = window.requestAnimationFrame.bind(window); window.__maxDpr = ${dpr};`);
await p.addInitScript(VCLOCK);
p.on("console", (m) => m.type() === "error" && console.log("console:", m.text()));
p.on("pageerror", (e) => console.log("pageerror:", e.message));
await p.goto(`http://127.0.0.1:5317/?replay=full-merged&shot=full`, { waitUntil: "networkidle" });
await p.waitForFunction(() => window.__replayReady === true, null, { timeout: 300000 });
await p.evaluate(() => document.fonts.ready);
const frame = async (t) => {
  await p.evaluate((t) => new Promise((res) => { window.__replayFull(t); window.__nativeRAF(() => window.__nativeRAF(() => res())); }), t);
  await p.evaluate((dt) => window.__step(dt), 1 / FPS);
};
if (MODE === "stills") {
  const [OUT, LIST] = rest;
  fs.mkdirSync(OUT, { recursive: true });
  for (const s of LIST.split(",").map(Number).sort((a, b) => a - b)) {
    for (let t = Math.max(0, s - 1); t < s - 1e-6; t += 1 / FPS) await frame(t);
    await frame(s);
    await p.screenshot({ path: `${OUT}/f-${s.toFixed(2).padStart(6, "0")}.jpg`, type: "jpeg", quality: 90 });
  }
} else {
  const [T0, T1, OUT] = rest;
  const t0 = +T0, t1 = +T1, n = Math.round((t1 - t0) * FPS);
  const ff = spawn("ffmpeg", ["-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", "30", "-c:v", "mjpeg", "-i", "-",
    "-vf", "scale=1920:1080:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "medium", "-crf", "12", "-r", "30", OUT], { stdio: ["pipe", "inherit", "inherit"] });
  for (let t = Math.max(0, t0 - 1); t < t0 - 1e-6; t += 1 / FPS) await frame(t);
  const t_start = Date.now();
  for (let i = 0; i < n; i++) {
    await frame(t0 + i / FPS);
    const buf = await p.screenshot({ type: "jpeg", quality: 92 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once("drain", r));
    if (i % 150 === 0) console.log(OUT, i, "/", n, ((Date.now() - t_start) / 1000).toFixed(0) + "s");
  }
  ff.stdin.end();
  await new Promise((r) => ff.on("close", r));
}
await b.close();
console.log("done");
