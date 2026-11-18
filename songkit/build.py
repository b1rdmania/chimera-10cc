"""songkit: make a song with Chimera the way 10cc made "I'm Not in Love".

    python songkit/build.py songs/daisy-bell.json

Reads one song file, renders every voice with Chimera, then mixes:
- the lead, plus a quiet out-of-tune double 12 ms behind it
- harmonies a third (or any number of scale steps) above or below the lead
- a tape-loop choir: one held vowel per chord note, 2-4 out-of-tune passes across
  male, female and child voices, always running at a low "gaffer tape" level and
  pushed up when its chord plays, each pass in its own place in the stereo field
Writes <out>/<name>.wav and .mp3. Needs CHIMERA (path to the chimera CLI), numpy, ffmpeg.
"""
import json, os, subprocess, sys, wave
from concurrent.futures import ThreadPoolExecutor
import numpy as np

SR = 48000
CHIMERA = os.environ.get('CHIMERA', 'chimera')
NOTE = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7,
        'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}
SCALES = {'major': [0, 2, 4, 5, 7, 9, 11], 'minor': [0, 2, 3, 5, 7, 8, 10]}
QUALITY = {'': [0, 4, 7], 'm': [0, 3, 7], '7': [0, 4, 7, 10], 'm7': [0, 3, 7, 10], 'maj7': [0, 4, 7, 11],
           '6': [0, 4, 7, 9], 'm6': [0, 3, 7, 9], 'sus4': [0, 5, 7], 'dim': [0, 3, 6]}

def chord_pcs(name):
    root = name[:2] if len(name) > 1 and name[1] in '#b' else name[:1]
    return [(NOTE[root] + i) % 12 for i in QUALITY[name[len(root):]]], NOTE[root]

def auto_chords(notes, bpb, key, scale):
    """Pick one diatonic chord per bar: the one whose notes cover the most melody time."""
    deg = [(key + s) % 12 for s in SCALES[scale]]
    cands = []
    for i, bonus in zip((0, 3, 4, 5, 1, 2), (0.3, 0.25, 0.25, 0.1, 0.05, 0.0)):   # I IV V vi ii iii
        root = deg[i]; pcs = [root, deg[(i + 2) % 7], deg[(i + 4) % 7]]
        cands.append((pcs, root, bonus))
    total = sum(d for _, d in notes); nbars = int(np.ceil(total / bpb)); weight = np.zeros((nbars, 12)); t = 0.0
    for m, d in notes:
        if m > 0:
            b0, b1 = t, t + d
            while b0 < b1 - 1e-9:
                bar = int(b0 // bpb); end = min(b1, (bar + 1) * bpb); weight[bar, int(m) % 12] += end - b0; b0 = end
        t += d
    out = []
    for bar in range(nbars):
        best = max(cands, key=lambda c: sum(weight[bar, p] for p in c[0]) / (weight[bar].sum() + 1e-9) + c[2])
        out.append((bar * bpb, bpb, best[0], best[1]))
    return out

def voicing(pcs, root):
    """Bass on the root, three chord tones in the middle, one high top note."""
    bass = 40 + (root - 40) % 12
    mid = []
    for p in pcs[1:] + pcs[:1]:
        m = 55 + (p - 55) % 12
        while m in mid: m += 12
        mid.append(m)
    top = 72 + (pcs[0] - 72) % 12
    return [bass] + sorted(mid)[:3] + [top]

def dia(m, steps, key, scale):
    pcs = {(key + s) % 12 for s in SCALES[scale]}; m = int(round(m)); d = 1 if steps > 0 else -1; k = 0
    if m % 12 not in pcs: m += d
    while k < abs(steps):
        m += d
        if m % 12 in pcs: k += 1
    return m

def render(job):
    path, body = job
    if not os.path.exists(path + '.wav'):
        subprocess.run([CHIMERA, 'render', 'notes', path + '.json', path, body], check=True, capture_output=True)
    return path

def load(path):
    w = wave.open(path + '.wav'); return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768

def main(song_path):
    S = json.load(open(song_path)); name = os.path.splitext(os.path.basename(song_path))[0]
    out = os.path.join(S.get('out', 'out'), name); os.makedirs(out + '/loops', exist_ok=True)
    bpm, bpb = S['bpm'], S.get('beats_per_bar', 4); B = 60 / bpm
    key, scale = NOTE[S['key']], S.get('scale', 'major')
    L = S['lead']; shift = 12 * L.get('octave', 0)
    notes = [[m + shift if m > 0 else 0, d] for m, d in L['notes']]
    pre = S.get('intro_bars', 2) * bpb                       # choir alone before the lead comes in
    lead_notes = [[0, pre]] + notes + [[0, 2]]
    total_beats = pre + sum(d for _, d in notes) + 2 * bpb
    # chords
    if S.get('chords', 'auto') == 'auto':
        ch = auto_chords(notes, bpb, key, scale)
    else:
        ch, t = [], 0.0
        for nm, beats in S['chords']:
            pcs, root = chord_pcs(nm); ch.append((t, beats, pcs, root)); t += beats
    chords = [((pre + b) * B, (pre + b + n) * B, voicing(pcs, root)) for b, n, pcs, root in ch]
    chords.insert(0, (0, pre * B, chords[0][2]))            # the intro holds the first chord
    end = total_beats * B
    # melody files (t0 = 0 so every render shares sample 0)
    jobs = []
    syl = json.loads(subprocess.run([CHIMERA, 'syllables', L['lyrics']], capture_output=True, text=True, check=True).stdout)
    nsung = sum(1 for m, _ in notes if m > 0)
    if len(syl) != nsung:
        sys.exit(f'lyrics give {len(syl)} syllables but the melody has {nsung} notes. Chimera splits: '
                 + ' '.join(x['text'] for x in syl) + '\nUse one word or syllable per note; "~" holds the last vowel over another note.')
    def write(path, nts, body, vib=30, syllables=None, lyrics=None):
        d = {'bpm': bpm, 'vibrato': vib, 't0': 0.0, 'notes': nts}
        if syllables is not None: d['syllables'] = syllables
        else: d['lyrics'] = lyrics
        json.dump(d, open(path + '.json', 'w')); jobs.append((path, body))
    write(f'{out}/lead', lead_notes, L.get('body', 'male'), syllables=syl)
    if S.get('double', True):
        write(f'{out}/double', [[m + 0.09 if m > 0 else 0, d] for m, d in lead_notes], L.get('body', 'male'), 22, syllables=syl)
    harms = []
    for h in S.get('harmonies', []):
        b0, b1 = (h.get('from_bar', 1) - 1) * bpb + pre, h.get('to_bar', 10 ** 6) * bpb + pre
        hn, t = [], 0.0
        for m, d in lead_notes:
            on = m > 0 and b0 <= t < b1
            hn.append([dia(m, h['steps'], key, scale) + 12 * h.get('octave', 0) if on else 0, d]); t += d
        sung = [i for i, (m, d) in enumerate(lead_notes) if m > 0]
        hs = [syl[k] for k, i in enumerate(sung) if hn[i][0] > 0]
        if not hs: continue
        write(f'{out}/h-{h["name"]}', hn, h.get('body', 'female'), 18, syllables=hs); harms.append(h)
    pitches = sorted({p for _, _, ps in chords for p in ps})
    loop_beats = 11.5 / B; C = S.get('choir', {}); vowel = C.get('vowel', 'ah'); npass = C.get('passes', 3)
    for p in pitches:
        seats = ([('male', 0), ('male', 7)] if p < 52 else
                 [('female', 0), ('child', 6), ('female', -5), ('child', -4)] if p >= 70 else
                 [('male', 0), ('female', -5), ('male', 7), ('female', 4)])[:max(2, npass)]
        for body, cents in seats:
            write(f'{out}/loops/p{p}-{body}{cents:+d}', [[p + cents / 100, loop_beats], [0, 1]], body, 8, lyrics=vowel)
    print(f'{name}: {len(jobs)} renders ({len(pitches)} choir notes)', flush=True)
    with ThreadPoolExecutor(os.cpu_count() or 4) as ex: list(ex.map(render, jobs))

    # ---------- mix ----------
    N = int((end + 3) * SR); t = np.arange(N) / SR; rng = np.random.default_rng(1975)
    def place(dst, x, at=0.0):
        i = int(at * SR); n = min(len(x), len(dst) - i)
        if n > 0: dst[i:i + n] += x[:n]
    padL, padR = np.zeros(N, np.float32), np.zeros(N, np.float32)
    floor, F = 10 ** (C.get('floor_db', -24) / 20), 0.6
    for p in pitches:
        e = np.full(N, floor, np.float32)
        for a, z, ps in chords:
            if p in ps:
                u = np.clip((t - (a - F / 2)) / F, 0, 1); dn = np.clip(((z + F / 2) - t) / F, 0, 1)
                e = np.maximum(e, (0.5 - 0.5 * np.cos(np.pi * np.minimum(u, dn))).astype(np.float32))
        e *= 10 ** (1.5 * np.sin(2 * np.pi * rng.uniform(0.03, 0.11) * t + rng.uniform(0, 6.3)) / 20)   # hands on faders
        files = sorted(f[:-4] for f in os.listdir(f'{out}/loops') if f.startswith(f'p{p}-') and f.endswith('.wav'))
        width = 0.35 if p < 52 else 1.0 if p >= 70 else 0.9
        for j, f in enumerate(files):
            x = load(f'{out}/loops/{f}'); seg = x[int(1.0 * SR):int(10.6 * SR)].copy(); k = int(0.4 * SR); Ls = len(seg) - k
            fade = np.sin(np.linspace(0, np.pi / 2, k)) ** 2; seg[:k] = seg[:k] * fade + seg[Ls:Ls + k] * (1 - fade); seg = seg[:Ls]
            off = rng.integers(0, Ls); loop = np.tile(seg, int(np.ceil((N + off) / Ls)) + 1)[off:off + N]
            g = (0.7 if p < 52 else 0.55 if p >= 70 else 1.0) / np.sqrt(len(files))
            pan = width * (1 if (j + p) % 2 else -1) * rng.uniform(0.65, 1.0); a = (pan + 1) * np.pi / 4
            padL += loop * e * g * np.cos(a) * 1.414; padR += loop * e * g * np.sin(a) * 1.414
    ramp = np.clip(t / 3, 0, 1) * np.clip((end + 2.5 - t) / 6, 0, 1); padL *= ramp; padR *= ramp
    lead = np.zeros(N, np.float32); place(lead, load(f'{out}/lead'))
    if S.get('double', True): place(lead, load(f'{out}/double') * 10 ** (-12 / 20), 0.012)
    hL, hR = np.zeros(N, np.float32), np.zeros(N, np.float32)
    for i, h in enumerate(harms):
        x = load(f'{out}/h-{h["name"]}'); side = h.get('pan', -0.7 if i % 2 == 0 else 0.7); a = (side + 1) * np.pi / 4
        place(hL, x * np.cos(a) * 1.2); place(hR, x * np.sin(a) * 1.2)
    for nm, x in (('padL', padL), ('padR', padR), ('lead', lead), ('hL', hL), ('hR', hR)): x.tofile(f'{out}/stem-{nm}.f32')
    R = ['-f', 'f32le', '-ar', str(SR), '-ac', '1']
    fc = ('[0]volume=0.22,chorus=0.6:0.9:40|55|70:0.4|0.35|0.3:0.25|0.3|0.4:2|2.5|3,lowpass=f=4500,aecho=0.8:0.85:110|230|410|690:0.45|0.35|0.25|0.18,equalizer=f=2000:t=q:w=1:g=-4[pl];'
          '[1]volume=0.22,chorus=0.6:0.9:45|62|77:0.4|0.35|0.3:0.3|0.27|0.45:2.2|2.7|3.3,lowpass=f=4500,aecho=0.8:0.85:135|265|455|740:0.45|0.35|0.25|0.18,equalizer=f=2000:t=q:w=1:g=-4[pr];'
          '[pl][pr]join=inputs=2:channel_layout=stereo[pad0];'
          '[2]volume=0.9,highpass=f=90,equalizer=f=3200:t=q:w=1.2:g=3,aecho=0.8:0.6:180|360:0.14|0.07,pan=stereo|c0=c0|c1=c0,asplit=2[ld][key];'
          '[pad0][key]sidechaincompress=threshold=0.04:ratio=2.5:attack=15:release=250[pad];'
          '[3][4]join=inputs=2:channel_layout=stereo,volume=0.7,highpass=f=120,aecho=0.8:0.75:150|310|520:0.35|0.25|0.15[hm];'
          '[pad][ld][hm]amix=inputs=3:normalize=0,loudnorm=I=-15:TP=-1.2:LRA=11[o]')
    ins = []
    for nm in ('padL', 'padR', 'lead', 'hL', 'hR'): ins += R + ['-i', f'{out}/stem-{nm}.f32']
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + ins + ['-filter_complex', fc, '-map', '[o]', '-ar', '44100', f'{out}/{name}.wav'], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', f'{out}/{name}.wav', '-b:a', '256k', f'{out}/{name}.mp3'], check=True)
    for nm in ('padL', 'padR', 'lead', 'hL', 'hR'): os.remove(f'{out}/stem-{nm}.f32')
    print(f'done: {out}/{name}.wav')

if __name__ == '__main__':
    main(sys.argv[1])
