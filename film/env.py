"""Measured loudness per track (10 Hz), from the real stems/renders, as fader levels 0..1."""
import json, wave, numpy as np
SR = 48000; HOP = SR // 10
def wav(f):
    w = wave.open(f); return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
def f32(f): return np.fromfile(f, np.float32)
def level(x, n):
    x = np.pad(x, (0, max(0, n * HOP - len(x))))[:n * HOP].reshape(n, HOP)
    db = 20 * np.log10(np.sqrt((x ** 2).mean(1)) + 1e-9)
    lv = np.clip((db + 50) / 40, 0, 1)
    out = np.zeros_like(lv); a = 0
    for i, v in enumerate(lv):                      # fast attack, slow release, like a meter
        a = v if v > a else a * 0.86 + v * 0.14; out[i] = a
    return out
N = int(225 * 10)
tr = {
    'lead': wav('full/lead.wav'), 'double': wav('full/lead-dbl.wav') * 0.25,
    'high': wav('full/harm-hi.wav'), 'low': wav('full/harm-lo.wav'), 'octave': wav('full/harm-oct.wav'),
    'lift': wav('full/harm-lift.wav'),
    'choir': (f32('full/stem-padL.f32') + f32('full/stem-padR.f32')) * 0.12,
    'kick': f32('full/stem-kick.f32') * 4, 'whisper': f32('full/stem-wh.f32') * 2,
}
env = {k: [round(float(v), 3) for v in level(x, N)] for k, x in tr.items()}
json.dump({'rate': 10, 'tracks': env}, open('film/env.json', 'w'))
for k, v in env.items():
    v = np.array(v); print(f'{k:8} active {np.mean(v > 0.3) * 100:5.1f}%  peak {v.max():.2f}')
