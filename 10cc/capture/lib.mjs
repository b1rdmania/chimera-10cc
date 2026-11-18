import { chromium } from "playwright-core";
import fs from "node:fs";
// Set CHROME_PATH to a Chrome for Testing binary, or leave it unset to use Playwright's own browser.
export const CHROME = process.env.CHROME_PATH || undefined;
export const launch = (headless = true) => chromium.launch({ ...(CHROME ? { executablePath: CHROME } : {}), headless, args: ["--autoplay-policy=no-user-gesture-required", "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] });
// Virtual clock: AudioContext time, performance.now and rAF are all driven by window.__step(dt).
export const VCLOCK = `(() => {
  let vt = 0, q = [], id = 0; const base = 1000;
  Object.defineProperty(BaseAudioContext.prototype, "currentTime", { get: () => vt, configurable: true });
  Object.defineProperty(AudioContext.prototype, "outputLatency", { get: () => 0, configurable: true });
  Object.defineProperty(BaseAudioContext.prototype, "baseLatency", { get: () => 0, configurable: true });
  AudioContext.prototype.getOutputTimestamp = () => ({ contextTime: 0, performanceTime: 0 });
  performance.now = () => base + vt * 1000;
  window.requestAnimationFrame = (cb) => { q.push([++id, cb]); return id; };
  window.cancelAnimationFrame = (i) => { q = q.filter(x => x[0] !== i); };
  window.__step = (dt) => { vt += dt; const c = q; q = []; for (const [, cb] of c) cb(base + vt * 1000); return vt; };
  window.__vt = () => vt;
})();`;
export const HIDE_UI = `.duet-top,.duet-bar,.screen-head{display:none!important} .screen,.screen.focus{border:0!important;box-shadow:none!important;outline:0!important} .duet{display:block!important;padding:0!important;height:100dvh!important} .duet-heads{display:block!important;height:100dvh!important} .duet-head{height:100dvh!important;border:0!important} .duet-head .screen-body{height:100dvh!important}`;
export const steps = (p, n, dt = 1 / 30) => p.evaluate(([n, dt]) => { for (let i = 0; i < n; i++) window.__step(dt); }, [n, dt]);
