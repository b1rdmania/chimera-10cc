"""Mix the full song from Chimera renders: tape-loop choir played on 'faders', lead + double,
mouth kick, whispers, hiss. Writes float stems; ffmpeg does the effects and the final mix."""
import json, wave, glob, re, subprocess
import numpy as np

SR = 48000
A = json.load(open('full/arr.json'))
END, B = A['end'], A['B']
N = int(END * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(1975)

def load(f):
    w = wave.open(f); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    assert w.getframerate() == SR, (f, w.getframerate()); return x

def place(dst, x, at):
    i = int(at * SR); n = min(len(x), len(dst) - i)
    if n > 0: dst[i:i + n] += x[:n]

def tape_loop(x, n, xf=0.4):
    """The steady middle of a sung 'ah', looped like a 12-foot tape loop with a crossfaded splice."""
    seg = x[int(1.0 * SR):int(10.8 * SR)].copy()
    k = int(xf * SR); L = len(seg) - k
    fade = np.sin(np.linspace(0, np.pi / 2, k)) ** 2
    seg[:k] = seg[:k] * fade + seg[L:L + k] * (1 - fade)       # splice: tail fades into head
    seg = seg[:L]
    off = rng.integers(0, L)                                    # stagger the splices
    reps = int(np.ceil((n + off) / L)) + 1
    return np.tile(seg, reps)[off:off + n]

# ---- fader envelopes per pitch: gaffer-tape floor at -24 dB, chords pushed up by hand
FLOOR, F = 10 ** (-24 / 20), 0.6
def envelope(p):
    e = np.full(N, FLOOR, np.float32)
    for a, z, c in A['chords']:
        if p not in c: continue
        up = np.clip((t - (a - F / 2)) / F, 0, 1); dn = np.clip(((z + F / 2) - t) / F, 0, 1)
        e = np.maximum(e, (0.5 - 0.5 * np.cos(np.pi * np.minimum(up, dn))).astype(np.float32))
    f, ph = rng.uniform(0.03, 0.11), rng.uniform(0, 2 * np.pi)
    return e * 10 ** (1.5 * np.sin(2 * np.pi * f * t + ph) / 20)    # hands on the faders

padL = np.zeros(N, np.float32); padR = np.zeros(N, np.float32)
files = sorted(glob.glob('full/loops/p*.wav'))
by_pitch = {}
for f in files: by_pitch.setdefault(int(re.search(r'/p(\d+)-', f).group(1)), []).append(f)
for p, fs in by_pitch.items():
    e = envelope(p); g = (0.7 if p < 50 else 0.55 if p >= 72 else 1.0) / np.sqrt(len(fs))
    width = 0.4 if p < 52 else 1.0 if p >= 72 else 0.95      # bass near centre, top line widest
    for j, f in enumerate(fs):
        x = tape_loop(load(f), N) * e * g
        pan = width * (1 if (j + p) % 2 else -1) * rng.uniform(0.65, 1.0)   # each pass its own seat
        a = (pan + 1) * np.pi / 4
        padL += x * np.cos(a) * 1.414; padR += x * np.sin(a) * 1.414
ramp = np.clip(t / 4.0, 0, 1) * np.clip((END - t) / 16.0, 0, 1)   # faders up at the top, long fade
padL *= ramp; padR *= ramp

lead = np.zeros(N, np.float32)
place(lead, load('full/lead.wav'), 0.0)
place(lead, load('full/lead-dbl.wav') * 10 ** (-12 / 20), 0.012)   # ADT-ish double, 12 ms late

# harmonies: hi panned left, lo right, octave + lift centre; set back with more reverb in master
harmL = np.zeros(N, np.float32); harmR = np.zeros(N, np.float32)
hi, lo = load('full/harm-hi.wav'), load('full/harm-lo.wav')
oc, li = load('full/harm-oct.wav') * 0.5, load('full/harm-lift.wav') * 0.55
place(harmL, hi * 0.85, 0.0); place(harmR, hi * 0.2, 0.0)
place(harmR, lo * 0.85, 0.0); place(harmL, lo * 0.2, 0.0)
for x in (oc, li): place(harmL, x * 0.6, 0.0); place(harmR, x * 0.6, 0.0)
# the break's "ooh" melody (transcribed from the original), centre
for f, g in (('full/ooh-female.wav', 0.75), ('full/ooh-child.wav', 0.45)):
    x = load(f) * g; place(harmL, x, 0.0); place(harmR, x, 0.0)

# the Rhodes-style fill (transcribed from separated stems): broken chords, each note struck and
# decaying like an electric piano, the whole instrument auto-panning at 5 Hz (its stereo vibrato)
def line_env(path):
    j = json.load(open(path)); e = np.zeros(N, np.float32); tt = 0.0
    for m, d in j['notes']:
        dur = d * B
        if m > 0:
            i0 = int(tt * SR); n = int((dur + 0.5) * SR); k = np.arange(n) / SR
            env = np.minimum(k / 0.008, 1) * np.exp(-k / 0.75)          # strike, then decay
            e[i0:i0 + n] = np.maximum(e[i0:i0 + n], env[:max(0, min(n, N - i0))])
        tt += dur
    return e
rh = np.zeros(N, np.float32)
for nm, g in (('top', 1.0), ('mid', 0.8), ('low', 0.7)):
    x = np.zeros(N, np.float32); place(x, load(f'full/rh-{nm}.wav'), 0.0)
    rh += x * line_env(f'full/rh-{nm}.json') * g
pan = 0.5 + 0.5 * 0.65 * np.sin(2 * np.pi * 5.0 * t)
fillL = rh * np.sqrt(1 - pan) * 1.2; fillR = rh * np.sqrt(pan) * 1.2

kick = np.zeros(N, np.float32)
k = load('fx/kick/pattern.wav'); L = int(16 * B * SR); k = k[:L]
a, z = A['kick']
for s in np.arange(a, z, 16 * B): place(kick, k, s)

wh = np.zeros(N, np.float32)
for at, name in A['whispers']: place(wh, load(f'fx/{name}.wav'), at)

# pink-ish hiss: white noise through a gentle 1/f tilt
w = rng.standard_normal(N).astype(np.float32)
hiss = np.cumsum(w) ; hiss -= np.convolve(hiss, np.ones(4800) / 4800, 'same'); hiss = 0.6 * hiss / np.abs(hiss).max() + 0.4 * w / np.abs(w).max()
hiss *= 10 ** (-46 / 20) * np.clip(t / 2, 0, 1) * np.clip((END - t) / 6, 0, 1)

for name, x in [('fillL', fillL), ('fillR', fillR), ('harmL', harmL), ('harmR', harmR), ('padL', padL), ('padR', padR), ('lead', lead), ('kick', kick), ('wh', wh), ('hiss', hiss)]:
    peak = np.abs(x).max() or 1
    print(name, 'peak', round(float(peak), 3))
    x.astype(np.float32).tofile(f'full/stem-{name}.f32')
