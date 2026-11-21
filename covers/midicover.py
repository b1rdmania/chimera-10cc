"""Cover a song from a hand-sequenced MIDI, every part sung by Chimera.
    CHIMERA=path/to/chimera python covers/midicover.py <song>/cover.json
See covers/README.md for the config fields. Needs numpy, mido, ffmpeg.
lyr: 'legato:<vowel>' (vowel on phrase starts, ~ after), 'each:<syl>' (one syllable per note), 'words:<w1 w2 ..>' (cycled per note),
     'phrases:<line1|line2|..>' (one line per phrase, exact-length line preferred),
     'whisper:<whisper.json>|<record_bpm>|<offset_s>' (word timings from whisper-cli -oj, mapped onto the notes)."""
import json, os, subprocess, sys, wave
from concurrent.futures import ThreadPoolExecutor
import numpy as np, mido
CH = os.path.abspath(os.path.expanduser(os.environ.get('CHIMERA', 'chimera'))) if os.sep in os.environ.get('CHIMERA', '') else os.environ.get('CHIMERA', 'chimera'); SR = 48000
cfg = json.load(open(sys.argv[1])); base = os.path.dirname(os.path.abspath(sys.argv[1])); os.chdir(base)
M = mido.MidiFile(cfg['midi']); TPB = M.ticks_per_beat
BPM = cfg.get('bpm') or next(mido.tempo2bpm(x.tempo) for tr in M.tracks for x in tr if x.type == 'set_tempo'); B = 60 / BPM
O = cfg.get('out', 'outm'); os.makedirs(O, exist_ok=True); KIT = os.path.join(O, 'kit')
def notes(i):
    t = 0; on = {}; out = []
    for x in M.tracks[i]:
        t += x.time
        if x.type == 'note_on' and x.velocity > 0: on[x.note] = (t, x.velocity)
        elif x.type in ('note_off', 'note_on') and x.note in on: (s, v) = on.pop(x.note); out.append((s / TPB, (t - s) / TPB, x.note, v))
    return sorted(out)
def voices(ns, k):
    groups = {}
    for x in ns: groups.setdefault(round(x[0], 2), []).append(x)
    lines = [[] for _ in range(k)]
    for s in sorted(groups):
        g = sorted(groups[s], key=lambda x: x[2])
        if len(g) > k: g = [g[0]] + g[-(k - 1):] if k > 1 else [g[-1]]
        for j, x in enumerate(g): lines[j].append(x)
    return lines
def seq(ns, min_d):
    ns = [x for x in ns if x[1] >= min_d]; out, t, kept = [], 0.0, []
    for i, (s, d, n, v) in enumerate(ns):
        if s < t - 1e-6: continue
        nxt = ns[i + 1][0] if i + 1 < len(ns) else s + d
        if s - t > 1e-6: out.append([0, round(s - t, 4)])
        dd = max(0.1, min(d, nxt - s)); out.append([n, round(dd, 4)]); kept.append((s, dd, n)); t = s + dd
    return out, kept
def phrases(kept, gap):
    ph, cur, t = [], [], -9
    for s, d, n in kept:
        if cur and s - t > gap: ph.append(cur); cur = []
        cur.append(n); t = s + d
    if cur: ph.append(cur)
    return ph
def lyrics(spec, kept):
    kind, _, arg = spec.partition(':')
    if kind == 'each': return ' '.join([arg] * len(kept))
    if kind == 'words': w = arg.split(); return ' '.join(w[i % len(w)] for i in range(len(kept)))
    if kind == 'legato':
        out = []
        for p in phrases(kept, 0.5): out += [arg] + ['~'] * (len(p) - 1)
        return ' '.join(out)
    if kind == 'phrases':
        lines = [l.split() for l in arg.split('|')]; out = []; li = 0
        for p in phrases(kept, 1.0):
            ex = [l for l in lines if len(l) == len(p)]; L = ex[0] if ex else lines[li % len(lines)]; li += 1
            out += (L + ['~'] * len(p))[:len(p)]
        return ' '.join(out)
    if kind == 'whisper':
        path, rbpm, off = arg.split('|'); rbpm, off = float(rbpm), float(off)
        seg = [x for x in json.load(open(path))['transcription'] if x['text'].strip()]
        words = [x['text'].strip() for x in seg]
        syl = json.loads(subprocess.run([CH, 'syllables', ' '.join(words)], capture_output=True, text=True).stdout)
        timed, wi, buf = [], 0, []
        for sy in syl:
            buf.append(sy)
            if sy.get('wordEnd'):
                a, b = seg[min(wi, len(seg) - 1)]['offsets']['from'] / 1000, seg[min(wi, len(seg) - 1)]['offsets']['to'] / 1000
                for j, x in enumerate(buf): timed.append((a + (b - a) * j / len(buf), x))
                buf = []; wi += 1
        out, p, prev = [], 0, None
        for s0, d0, n in kept:
            T = s0 * 60 / rbpm + off; E = T + d0 * 60 / rbpm
            while p < len(timed) and timed[p][0] < T - 0.6: p += 1
            if p < len(timed) and timed[p][0] <= E + 0.25: x = dict(timed[p][1]); p += 1
            elif prev is not None: x = {'text': '~', 'onset': [], 'nucleus': prev['nucleus'], 'coda': [], 'melisma': True, 'wordEnd': True, 'phraseEnd': False}
            else: x = json.loads(subprocess.run([CH, 'syllables', 'ah'], capture_output=True, text=True).stdout)[0]
            out.append(x); prev = x
        return out
    raise SystemExit('bad lyr ' + spec)
jobs, mixmap = [], []
for pi, P in enumerate(cfg['parts']):
    ns = [(s, d, n + P.get('transpose', 0), v) for s, d, n, v in notes(P['track'])]
    lines = voices(ns, P.get('k', 3)) if P.get('mode') == 'poly' else [ns]
    for li, line in enumerate(lines):
        if not line: continue
        s, kept = seq(line, P.get('min_d', 0.12))
        if not kept: continue
        ly = lyrics(P['lyr'], kept)
        for ci, (body, cents, octv, pan, gain) in enumerate(P['copies']):
            name = f"p{pi}-{P.get('name', 't' + str(P['track']))}-v{li}-c{ci}"
            if P.get('mode') == 'poly': pan = max(-1, min(1, pan + (li - (len(lines) - 1) / 2) * P.get('spread', 0.5)))
            nn = [[m + 12 * octv + cents / 100 if m else 0, d] for m, d in s]
            d = {'bpm': BPM, 'vibrato': P.get('vib', 20), 't0': 0.0, 'notes': nn}
            if isinstance(ly, list): d['syllables'] = ly
            else: d['lyrics'] = ly
            json.dump(d, open(f'{O}/{name}.json', 'w'))
            jobs.append((name, body)); mixmap.append((name, P.get('bus', 'v'), pan, gain))
bad = 0
for n, b in jobs:
    d = json.load(open(f'{O}/{n}.json')); want = sum(1 for m, _ in d['notes'] if m)
    if 'syllables' in d:
        if len(d['syllables']) != want: print('SYL COUNT BAD', n, len(d['syllables']), want)
        continue
    got = len(json.loads(subprocess.run([CH, 'syllables', d['lyrics']], capture_output=True, text=True).stdout))
    if got != want:
        bad += 1; d['lyrics'] = ' '.join(['ah'] * want); json.dump(d, open(f'{O}/{n}.json', 'w')); print('syllable fallback', n, got, want)
def render(j):
    n, b = j
    if not os.path.exists(f'{O}/{n}.wav'): subprocess.run([CH, 'render', 'notes', f'{O}/{n}.json', f'{O}/{n}', b], check=True, capture_output=True)
print(f'{len(jobs)} renders at {BPM:.1f} bpm', flush=True)
with ThreadPoolExecutor(os.cpu_count()) as ex: list(ex.map(render, jobs))
def load(p):
    w = wave.open(p); return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
END = max(s + d for P in cfg['parts'] for s, d, n, v in notes(P['track'])) * B + 5
N = int((END + 4) * SR); st = {k: np.zeros(N, np.float32) for k in ('vL', 'vR', 'cL', 'cR', 'b', 'dL', 'dR')}
def put(x, bus, pan, g, at=0.0):
    i = int(at * SR); n = min(len(x), N - i)
    if n <= 0: return
    if bus == 'b': st['b'][i:i + n] += x[:n] * g; return
    a = (pan + 1) * np.pi / 4; L, R = {'v': ('vL', 'vR'), 'c': ('cL', 'cR'), 'd': ('dL', 'dR')}[bus]
    st[L][i:i + n] += x[:n] * g * np.cos(a) * 1.414; st[R][i:i + n] += x[:n] * g * np.sin(a) * 1.414
for name, bus, pan, g in mixmap: put(load(f'{O}/{name}.wav'), bus, pan, g)
def kitmap(n):
    if n in (35, 36): return 'B', 0, 1.0
    if n in (37, 38, 39, 40): return 'Pf', 0, .9
    if n in (42, 44, 69, 70, 82, 54): return 't', .3, .4
    if n == 46: return 'tss', .3, .4
    if n in (49, 51, 52, 55, 57, 59): return 'kch', 0, .45
    if 41 <= n <= 50: return 'B', (n - 45) / 6, .55
    if n in (75, 76, 77): return 'K', -.3, .5
    return 'K', -.2, .35
smp = {}
D = cfg.get('drums', {})
if D.get('tracks') and not os.path.exists(f'{KIT}/B.wav'):   # beatbox kit: one Chimera render per sound
    subprocess.run([CH, 'render', 'beatbox', KIT, 'B Pf t tss kch K', D.get('body', 'male'), '100', '1'], check=True, capture_output=True)
for tr in D.get('tracks', []):
    for s, d, n, v in notes(tr):
        nm, pan, g = kitmap(n); smp.setdefault(nm, load(f'{KIT}/{nm}.wav')); put(smp[nm], 'd', pan, g * (v / 100) * D.get('gain', 1.0), s * B)
for k, v in st.items(): v.tofile(f'{O}/stem-{k}.f32')
I = []
for k in ('vL', 'vR', 'cL', 'cR', 'b', 'dL', 'dR'): I += ['-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', f'{O}/stem-{k}.f32']
fx = cfg.get('fx', {})
fc = (f"[0][1]join=inputs=2:channel_layout=stereo,highpass=f=90,equalizer=f=3000:t=q:w=1:g=2,aecho=0.8:{fx.get('vwet', 0.85)}:170|340|580|900:0.42|0.32|0.22|0.15,asplit=2[v][key];"
      f"[2][3]join=inputs=2:channel_layout=stereo,volume={fx.get('choir', 0.7)},chorus=0.6:0.9:45|60:0.4|0.3:0.3|0.4:2|2.6,lowpass=f=5500,aecho=0.8:0.88:140|290|500|800:0.5|0.4|0.3|0.2[c0];"
      "[c0][key]sidechaincompress=threshold=0.05:ratio=2:attack=20:release=300[c];"
      f"[4]volume={fx.get('bass', 1.4)},lowpass=f=400,equalizer=f=65:t=q:w=1:g=8,pan=stereo|c0=c0|c1=c0[b];"
      f"[5][6]join=inputs=2:channel_layout=stereo,volume={fx.get('drums', 1.8)},equalizer=f=70:t=q:w=1:g=6,highshelf=f=5000:g=8,aecho=0.8:0.35:70:0.12[d];"
      "[v][c][b][d]amix=inputs=4:normalize=0,loudnorm=I=-14:TP=-1.2[o]")
name = cfg['name']
subprocess.run(['ffmpeg', '-y', '-v', 'error'] + I + ['-filter_complex', fc, '-map', '[o]', '-ar', '44100', f'{name}.wav'], check=True)
subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', f'{name}.wav', '-b:a', '256k', f'{name}.mp3'], check=True)
for k in st: os.remove(f'{O}/stem-{k}.f32')
print('done', os.path.join(base, name + '.mp3'), round(END, 1), 's', bad, 'fallbacks')
