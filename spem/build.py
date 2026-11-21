"""Spem in alium (Tallis) sung by Chimera: 40 independent voices, 8 choirs.

    python spem/build.py [--seconds N] [--tag NAME] [--only 1.treble,2.bass] [--bpm 120]

Score: Brighton Consort / David Siu MIDI (see score.py). Writes spem/out/<tag>/ and spem/out/spem-in-alium*.wav/.mp3
"""
import argparse, json, os, subprocess, sys, time, wave
from concurrent.futures import ThreadPoolExecutor
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score

HERE = os.path.dirname(os.path.abspath(__file__)); os.chdir(HERE)
SR = 48000
CHIMERA = os.environ.get('CHIMERA', os.path.expanduser('~/Documents/chimera-vocal-synth/target/release/chimera'))
# voice -> (body, octave shift, gain)
def voice_map(choir, voice):
    if voice == 'treble': return ('child' if choir % 2 == 0 else 'female', 0, 1.0)
    if voice == 'mean': return ('female', 0, 1.0)
    if voice == 'alto': return ('female', 0, 1.0)
    if voice == 'tenor': return ('male', 0, 1.0)
    return ('male', 0, 1.0)

def make_job(p, out, bpm, tmax_beats, rng):
    notes = p['notes']; syl = score.to_chimera(notes, score.underlay(notes))
    seq = []; sy = []; t = 0.0
    body, octv, gain = voice_map(p['choir'], p['voice'])
    detune = rng.uniform(-0.12, 0.12)
    for (s, d, m), sg in zip(notes, syl):
        if s >= tmax_beats: break
        if s > t + 1e-6: seq.append([0, s - t]); t = s
        seq.append([m + 12 * octv + detune, d]); sy.append(sg); t = s + d
    name = f'{out}/c{p["choir"]}-{p["voice"]}'
    json.dump({'bpm': bpm, 'vibrato': 22, 't0': 0.0, 'notes': seq, 'syllables': sy}, open(name + '.json', 'w'))
    return name, body, gain

def render(job):
    name, body, _ = job
    if not os.path.exists(name + '.wav'):
        t0 = time.time()
        subprocess.run([CHIMERA, 'render', 'notes', name + '.json', name, body], check=True, capture_output=True)
        print(f'  {os.path.basename(name)} {time.time()-t0:.0f}s', flush=True)
    return name

def load(path):
    w = wave.open(path + '.wav'); assert w.getframerate() == SR, w.getframerate()
    return np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--seconds', type=float, default=0); ap.add_argument('--tag', default='full')
    ap.add_argument('--only', default=''); ap.add_argument('--bpm', type=float, default=120); ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--no-mix', action='store_true'); ap.add_argument('--skip-until', type=float, default=0)
    a = ap.parse_args()
    out = f'out/{a.tag}'; os.makedirs(out, exist_ok=True); B = 60 / a.bpm
    tmax = a.seconds / B if a.seconds else 1e9
    parts = score.parse(); rng = np.random.default_rng(1570)
    if a.only: keep = set(a.only.split(',')); parts = [p for p in parts if f'{p["choir"]}.{p["voice"]}' in keep]
    jobs = [make_job(p, out, a.bpm, tmax, rng) for p in parts]
    keepj = [i for i, (n, _, _) in enumerate(jobs) if json.load(open(n + '.json'))['syllables']]
    parts = [parts[i] for i in keepj]; jobs = [jobs[i] for i in keepj]; t0 = time.time()
    with ThreadPoolExecutor(a.workers) as ex: list(ex.map(render, jobs))
    print(f'rendered {len(jobs)} parts in {time.time()-t0:.0f}s', flush=True)
    if a.no_mix: return
    mix(parts, jobs, out, a.tag, a.seconds)

def mix(parts, jobs, out, tag, seconds):
    xs = [load(n) for n, _, _ in jobs]; N = max(len(x) for x in xs) + SR * 2
    rng = np.random.default_rng(7)
    L = np.zeros(N, np.float32); R = np.zeros(N, np.float32)
    voice_off = {'treble': 0.0, 'mean': 0.14, 'alto': -0.14, 'tenor': 0.07, 'bass': -0.07}
    for p, x, (_, body, g) in zip(parts, xs, jobs):
        rms = np.sqrt(np.mean(x[np.abs(x) > 1e-4] ** 2)) if np.any(np.abs(x) > 1e-4) else 1
        x = x / rms * 0.05 * g
        pos = -0.92 + 1.84 * (p['choir'] - 1) / 7 + voice_off[p['voice']] * 0.45 + rng.uniform(-0.03, 0.03)
        pos = float(np.clip(pos, -1, 1)); ang = (pos + 1) * np.pi / 4
        i = int(rng.uniform(0, 0.02) * SR)
        L[i:i + len(x)] += x * np.cos(ang); R[i:i + len(x)] += x * np.sin(ang)
    np.stack([L, R], 1).astype(np.float32).tofile(f'{out}/dry.f32')
    # cathedral IR: decorrelated exponentially decaying noise, RT60 about 5 s, darker tail
    irn = int(5.5 * SR); tt = np.arange(irn) / SR; ir = []
    for ch in range(2):
        r = np.random.default_rng(100 + ch).standard_normal(irn).astype(np.float32)
        env = np.exp(-6.9 * tt / 5.0) * np.clip(tt / 0.04, 0, 1)
        y = r * env; k = np.exp(-tt / 0.0006); k = None
        # one-pole low-pass sweeping darker with time (cheap: blend of progressively smoothed copies)
        s1 = np.convolve(y, np.ones(4) / 4, 'same'); s2 = np.convolve(y, np.ones(16) / 16, 'same')
        w = np.clip(tt / 4.0, 0, 1); y = y * (1 - np.minimum(w * 2, 1)) + s1 * np.clip(w * 2, 0, 1) * (1 - w) + s2 * w
        ir.append(y)
    ir = np.stack(ir, 1); ir /= np.sqrt((ir ** 2).sum(0).mean())
    ir.astype(np.float32).tofile(f'{out}/ir.f32')
    R_ = lambda f: ['-f', 'f32le', '-ar', str(SR), '-ac', '2', '-i', f]
    fc = ('[0]asplit=2[d][w0];[1]volume=1[ir];[w0][ir]afir=dry=0:wet=1:length=1:gtype=none:irgain=0.07[w];'
          '[d]volume=0.8[d2];[w]volume=1.0,highpass=f=120[w2];[d2][w2]amix=inputs=2:normalize=0,'
          'equalizer=f=250:t=q:w=1:g=-2,loudnorm=I=-16:TP=-1.5:LRA=11[o]')
    wav = f'out/{"spem-in-alium" if not seconds else "spem-in-alium-" + tag}.wav'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error'] + R_(f'{out}/dry.f32') + R_(f'{out}/ir.f32') + ['-filter_complex', fc, '-map', '[o]', '-ar', '44100', wav], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-b:a', '224k', wav[:-4] + '.mp3'], check=True)
    os.remove(f'{out}/dry.f32'); os.remove(f'{out}/ir.f32')
    print('done', wav, flush=True)

if __name__ == '__main__':
    main()
