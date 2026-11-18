"""Data for the full merged film: public/shows/full-merged/ in the local Chimera checkout (gitignored).

Choir = mix.py's tape-loop machine, replayed exactly: its rng (seed 1975) is stepped in mix.py's
order, giving every pass's tape offset and every pitch's fader (chords up, -24 dB floor, the
"hands on the faders" wobble, the 4 s fade-in and the 16 s fade-out). Every pass (105 loop files)
is re-rendered with --tele into film2/tele/loops/ and checked bit-identical to full/loops/.
Voices: lead, double, high, low, octave, lift (full/*.tele, written by render.sh), ooh female/child (re-rendered).
Run: film2/.venv/bin/python film2/tools/prep3.py [--render]"""
import json, glob, re, os, sys, shutil, wave, subprocess
from concurrent.futures import ThreadPoolExecutor
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CHIM = os.path.abspath(os.path.expanduser(os.environ.get('CHIMERA_REPO', '../chimera-vocal-synth')))
OUT = f'{CHIM}/public/shows/full-merged'
TELE = f'{ROOT}/film2/tele'
CLI = f'{CHIM}/target/release/chimera'
os.makedirs(OUT, exist_ok=True); os.makedirs(f'{TELE}/loops', exist_ok=True)
SR = 48000
A = json.load(open(f'{ROOT}/full/arr.json')); END = A['end']; CH = sorted(A['chords'])
FPS = 30; tt = np.arange(int(END * FPS) + 2) / FPS
rng = np.random.default_rng(1975)
FLOOR, F = 10 ** (-24 / 20), 0.6
def envelope(p, t):
    e = np.full(len(t), FLOOR)
    for a, z, c in A['chords']:
        if p not in c: continue
        up = np.clip((t - (a - F / 2)) / F, 0, 1); dn = np.clip(((z + F / 2) - t) / F, 0, 1)
        e = np.maximum(e, 0.5 - 0.5 * np.cos(np.pi * np.minimum(up, dn)))
    f, ph = rng.uniform(0.03, 0.11), rng.uniform(0, 2 * np.pi)
    return e * 10 ** (1.5 * np.sin(2 * np.pi * f * t + ph) / 20)
files = sorted(glob.glob(f'{ROOT}/full/loops/p*.wav'))
by_pitch = {}
for f in files: by_pitch.setdefault(int(re.search(r'/p(\d+)-', f).group(1)), []).append(f)
ramp = np.clip(tt / 4.0, 0, 1) * np.clip((END - tt) / 16.0, 0, 1)
seg = int(10.8 * SR) - int(1.0 * SR); L = seg - int(0.4 * SR)
pitches, passes = [], []
for p, fs in by_pitch.items():
    e = envelope(p, tt)
    pos = np.clip(1 + 20 * np.log10(np.maximum(e * ramp, 1e-6)) / 28.6, 0, 1)
    pitches.append({'midi': p, 'fader': [round(float(x), 3) for x in pos]})
    for j, f in enumerate(fs):
        off = int(rng.integers(0, L)) / SR
        rng.uniform(0.65, 1.0)                     # the pan draw
        stem = os.path.basename(f)[:-4]
        passes.append({'stem': stem, 'midi': p, 'body': stem.split('-')[1], 'pass': j, 'off': round(off, 5)})
print(len(pitches), 'pitches', len(passes), 'passes')

def render(args):
    json_in, out, body = args
    if not os.path.exists(out + '.tele'):
        subprocess.run([CLI, 'render', 'notes', json_in, out, body, '--tele', out + '.tele'], check=True, capture_output=True)
if '--render' in sys.argv:
    jobs = [(f'{ROOT}/full/loops/{q["stem"]}.json', f'{TELE}/loops/{q["stem"]}', q['body']) for q in passes]
    jobs += [(f'{ROOT}/full/ooh-{b}.json', f'{TELE}/ooh-{b}', b) for b in ('female', 'child')]
    with ThreadPoolExecutor(8) as ex: list(ex.map(render, jobs))
    bad = [q['stem'] for q in passes if open(f'{TELE}/loops/{q["stem"]}.wav', 'rb').read() != open(f'{ROOT}/full/loops/{q["stem"]}.wav', 'rb').read()]
    bad += [b for b in ('female', 'child') if open(f'{TELE}/ooh-{b}.wav', 'rb').read() != open(f'{ROOT}/full/ooh-{b}.wav', 'rb').read()]
    print('re-renders not bit-identical:', bad or 'none')

for q in passes: shutil.copy(f'{TELE}/loops/{q["stem"]}.tele', f'{OUT}/{q["stem"]}.tele')
voices = {'lead': f'{ROOT}/full/lead.tele', 'double': f'{ROOT}/full/lead-dbl.tele', 'high': f'{ROOT}/full/harm-hi.tele',
          'low': f'{ROOT}/full/harm-lo.tele', 'octave': f'{ROOT}/full/harm-oct.tele', 'lift': f'{ROOT}/full/harm-lift.tele',
          'oohf': f'{TELE}/ooh-female.tele', 'oohc': f'{TELE}/ooh-child.tele'}
for k, src in voices.items(): shutil.copy(src, f'{OUT}/{k}.tele')
w = wave.open(f'{ROOT}/full/lead.wav'); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype('<f4') / 32768
x.tofile(f'{OUT}/lead.f32')

def notes(path, fixed=None):
    d = json.load(open(path)); spb = 60 / d['bpm']; t = d.get('t0', 0.0); si = 0; out = []
    for m, b in d['notes']:
        if m > 0:
            if fixed: show = fixed
            else:
                s = d['syllables'][si]; si += 1
                ipa = ''.join(p['ipa'] for p in s['onset']) + s['nucleus']['ipa'] + ''.join(p['ipa'] for p in s['coda'])
                show = out[-1]['show'] if s.get('melisma') and out and len(ipa) == 1 else ipa
            out.append({'midi': m, 't0': round(t, 4), 't1': round(t + b * spb, 4), 'show': show})
        t += b * spb
    return out
NOTES = {'lead': notes(f'{ROOT}/full/lead.json'), 'high': notes(f'{ROOT}/full/harm-hi.json'), 'low': notes(f'{ROOT}/full/harm-lo.json'),
         'octave': notes(f'{ROOT}/full/harm-oct.json'), 'lift': notes(f'{ROOT}/full/harm-lift.json'),
         'oohf': notes(f'{ROOT}/full/ooh-female.json', 'u'), 'oohc': notes(f'{ROOT}/full/ooh-child.json', 'u')}
ENV = json.load(open(f'{ROOT}/film/env.json'))
def level(x, n, HOP=SR // 10):                      # film/env.py's meter: fast attack, slow release
    x = np.pad(x, (0, max(0, n * HOP - len(x))))[:n * HOP].reshape(n, HOP)
    lv = np.clip((20 * np.log10(np.sqrt((x ** 2).mean(1)) + 1e-9) + 50) / 40, 0, 1); out = np.zeros_like(lv); a = 0
    for i, v in enumerate(lv): a = v if v > a else a * 0.86 + v * 0.14; out[i] = a
    return out
for k, b in (('oohf', 'female'), ('oohc', 'child')):
    w = wave.open(f'{ROOT}/full/ooh-{b}.wav'); x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    ENV['tracks'][k] = [round(float(v), 3) for v in level(x, len(ENV['tracks']['lead']))]
json.dump({'fps': FPS, 'end': END, 'pitches': pitches, 'passes': passes, 'notes': NOTES, 'env': ENV['tracks'], 'envRate': ENV['rate'],
           'chords': CH}, open(f'{OUT}/full.json', 'w'), ensure_ascii=False)
print('wrote', OUT)
