"""Full 'I'm Not in Love' (official video edit timeline) with Chimera.
Writes melody JSON per vocal line, loop JSON per pitch/pass, and the arrangement (arr.json)
that mix.py renders. Song time == video time (VEVO edit STugQ0X1NoI)."""
import json, subprocess, os, sys

C = os.environ.get('CHIMERA', 'chimera')   # path to the chimera CLI
BPM = 67.0; B = 60 / BPM
SEC = 16 * B                     # one 16-beat block
K0 = 0.57                        # intro block start (verse 1 = K0 + SEC, fitted to captions)
def blk(k): return K0 + k * SEC

def ht(sec):
    s = open(f'ht-{sec}.json').read(); return json.loads(json.loads(s[s.find('{'):])['jsonData'])

MINOR = {'1': 0, '2': 2, '3': 3, '4': 5, '5': 7, '6': 8, '7': 10, '#7': 11}
MAJOR = {'1': 0, '2': 2, '3': 4, '4': 5, '5': 7, '6': 9, '7': 11}
def notes_of(j, tonic, scale, b0, b1):
    """[(beat, dur, midi)] for tab beats in [b0, b1)."""
    out = []
    for n in j['notes']:
        if n['isRest'] or not (b0 <= n['beat'] < b1): continue
        out.append((n['beat'], n['duration'], tonic + scale[n['sd']] + 12 * n['octave']))
    return out

V = ht('verse'); CH = ht('chorus'); BR = ht('bridge')
# phrases: (first tab beat, last tab beat) per half-verse, 4 phrases each
VA = [(1, 5), (5, 9), (9, 12.4), (12.4, 17)]
VB = [(17, 21), (21, 25), (25, 27.6), (27.6, 33)]
CHP = [(1, 4), (4, 7), (7, 17)]

def phrase(j, tonic, scale, rng):
    return [(b, min(d, rng[1] - b), m) for b, d, m in notes_of(j, tonic, scale, *rng)]

lines = []  # (song_time_of_tab_beat_1_of_section, notes[(beat,dur,midi)], syllable string)
def section(t_start, j, tonic, scale, ranges, lyrics):
    for rng, lyr in zip(ranges, lyrics):
        ns = phrase(j, tonic, scale, rng)
        lines.append((t_start, ns, lyr))

VERSE = (V, 61, MINOR)   # C# minor, tonic C#4
CHOR = (CH, 64, MAJOR)   # E major, tonic E4
BRID = (BR, 67, MAJOR)   # G major, tonic G4

# words come straight from the official captions (never typed or printed here)
import re
_v = open('src/official.en.vtt').read()
CUES = []
for m in re.finditer(r'(\d\d):(\d\d):(\d\d\.\d+) --> [^\n]+\n(.+?)(?:\n\n|\Z)', _v, re.S):
    if '♪' not in m.group(4): continue
    txt = re.sub(r'[♪()]', '', m.group(4).replace('\n', ' '))
    CUES.append(re.findall(r"[A-Za-z']+[,.!?]?", txt))
def nsyl(words):
    w = ' '.join(x.rstrip(',.!?') for x in words)
    return len(json.loads(subprocess.run([C, 'syllables', w], capture_output=True, text=True).stdout)) if w else 0
def split2(words, n1, n2):
    best = None
    for k in range(1, len(words)):
        cost = abs(nsyl(words[:k]) - n1) + abs(nsyl(words[k:]) - n2) - (0.5 if words[k - 1][-1] in ',.!?' else 0)
        if best is None or cost < best[0]: best = (cost, k)
    k = best[1]; return words[:k], words[k:]
clean = lambda ws: ' '.join(x.rstrip(',.!?') for x in ws)
cue = iter(CUES)
def take(j, tonic, scale, ranges, plan):
    """plan: per phrase 1 = its own cue, 2 = one cue split across this and the next phrase."""
    out, i = [], 0
    while i < len(ranges):
        if plan[i] == 2:
            a, b = split2(next(cue), len(phrase(j, tonic, scale, ranges[i])), len(phrase(j, tonic, scale, ranges[i + 1])))
            out += [clean(a), clean(b)]; i += 2
        else:
            out.append(clean(next(cue))); i += 1
    return out
CH12 = (CH, 64, MAJOR)
section(blk(1), *VERSE, VA, take(*VERSE, VA, [1, 1, 2, 0]))
section(blk(2) - SEC, *VERSE, VB, take(*VERSE, VB, [1, 1, 1, 1]))
section(blk(3), *CHOR, CHP, take(*CHOR, CHP, [1, 1, 1]))
section(blk(4), *VERSE, VA, take(*VERSE, VA, [1, 1, 2, 0]))
section(blk(5) - SEC, *VERSE, VB, take(*VERSE, VB, [1, 1, 2, 0]))
section(blk(6), *CHOR, CHP, take(*CHOR, CHP, [2, 0, 1]))
section(blk(10), *VERSE, VA, take(*VERSE, VA, [1, 1, 2, 0]))
section(blk(11) - SEC, *VERSE, VB, take(*VERSE, VB, [1, 1, 2, 0]))
CHP3 = [(1, 4), (4, 7), (7, 12)]          # chorus 3 cut short: the bridge comes in over it
section(blk(12), *CHOR, CHP3, take(*CHOR, CHP3, [2, 0, 1]))
T_BRIDGE = blk(12) + 12 * B + 0.35
section(T_BRIDGE, *BRID, [(1, 9), (9, 17)], take(*BRID, [(1, 9), (9, 17)], [1, 1]))
T_OUT = T_BRIDGE + 16 * B + 0.35
o1, o2 = next(cue), next(cue)
section(T_OUT, *VERSE, [(1, 5)], [clean(o1)])
lines.append((T_OUT, [(b + 4, d, m) for b, d, m in lines[-1][1]], clean(o2)))

def sylobjs(text):
    return json.loads(subprocess.run([C, 'syllables', text], capture_output=True, text=True).stdout)

def fit(ns, text):
    """Notes and syllable objects for one line, equal in number: split the longest notes when
    there are more syllables, hold the last vowel as a melisma when there are more notes."""
    ns = list(ns); so = sylobjs(text)
    while len(ns) < len(so):
        i = max(range(len(ns)), key=lambda i: ns[i][1]); b, d, m = ns[i]
        ns[i:i + 1] = [(b, d / 2, m), (b + d / 2, d / 2, m)]
    if len(so) < len(ns):
        so = sylobjs(text + ' ~' * (len(ns) - len(so)))
    assert len(so) == len(ns), (len(so), len(ns))
    return ns, so

events = []
for t0, ns, text in lines:
    ns, so = fit(ns, text)
    for (b, d, m), sy in zip(ns, so):
        events.append((t0 + (b - 1) * B, d * B, m, sy))
events.sort(key=lambda e: e[0])
notes, syl, t = [], [], 0.0
for ts, ds, m, sy in events:
    if ts > t + 1e-4: notes.append([0, (ts - t) / B])
    elif ts < t - 1e-4: print('overlap at', round(ts, 3), 'prev end', round(t, 3))
    notes.append([m, ds / B]); syl.append(sy); t = ts + ds
notes.append([0, 1])
sounding = sum(1 for n in notes if n[0] > 0)
assert len(syl) == sounding, (len(syl), sounding)
# t0 shifts the whole file: first event time minus T0 is carried by the leading rest
json.dump({'bpm': BPM, 'vibrato': 30, 't0': 0.0, 'syllables': syl, 'notes': notes}, open('full/lead.json', 'w'))
json.dump({'bpm': BPM, 'vibrato': 22, 't0': 0.0, 'syllables': syl,
           'notes': [[n[0] + 0.09 if n[0] > 0 else 0, n[1]] for n in notes]}, open('full/lead-dbl.json', 'w'))

# ---- chords: (start_s, end_s, [midi]) for the loop faders
A6, Am6 = [45, 57, 61, 64, 66], [45, 57, 60, 64, 66]
Gsm7, Gs7B = [44, 56, 59, 63, 66], [48, 60, 63, 66, 68]
Csm, Csm7 = [49, 56, 61, 64, 68], [49, 59, 61, 64, 68]
VCH = [(4, A6), (4, Am6), (2, Gsm7), (2, Gs7B), (2, Csm), (2, Csm7)]
B11, Bmaj, B13, Gs7b9 = [47, 57, 61, 64, 69], [47, 59, 63, 66, 71], [47, 57, 63, 68, 69], [48, 56, 60, 63, 66]
ICH = [(4, B11), (4, Bmaj), (4, B11), (1.5, Bmaj), (1.5, B13), (1, Gs7b9)]
Amaj, Bm = [45, 57, 61, 64, 69], [47, 59, 63, 66, 71]
E, AoE, Em7 = [40, 56, 59, 64, 68], [40, 57, 61, 64, 69], [40, 55, 59, 62, 64]
CCH = [(4, Amaj), (4, Bm), (1.5, E), (2.5, AoE), (1.5, Em7), (2.5, AoE)]
Am, Am7G, DoFs, G, Gmaj7Fs, Em7b, Em7D, Em11, EoGs = (
    [45, 57, 60, 64, 69], [43, 57, 60, 64, 67], [42, 57, 62, 66, 69], [43, 55, 59, 62, 67],
    [42, 55, 59, 62, 66], [40, 55, 59, 62, 64], [38, 55, 59, 62, 64], [40, 55, 57, 62, 66], [44, 56, 59, 64, 68])
BCH = [(1, Am), (1, Am7G), (2, DoFs), (1, G), (1, Gmaj7Fs), (1, Em7b), (1, Em7D), (1, Am)]
chords = []
def run(t, seq, reps=1):
    for _ in range(reps):
        for d, c in seq: chords.append((t, t + d * B, c)); t += d * B
    return t
run(blk(0), ICH)
for k in (1, 2, 4, 5, 10, 11): run(blk(k), VCH)
for k in (3, 6): run(blk(k), CCH)
run(blk(12), CCH[:3] + [(2.5, AoE)])                         # chorus 3, 12 beats
run(blk(7), VCH); run(blk(8), ICH); run(blk(9), VCH)          # instrumental + whispers
t = run(T_BRIDGE, BCH + [(2, Am), (2, DoFs), (2.5, Em11), (1.5, EoGs)])   # 16 beats of bridge
t = run(T_OUT, [(4, A6), (4, Am6), (4, A6), (4, Am6), (4, A6), (4, Am6), (8, E)])  # outro + fade
END = 225.0
# the record's choir top line (heard in the original's side channel): one high note per chord
TOP = {tuple(A6): 76, tuple(Am6): 76, tuple(Gsm7): 75, tuple(Gs7B): 75, tuple(Csm): 80, tuple(Csm7): 80,
       tuple(B11): 75, tuple(Bmaj): 75, tuple(B13): 75, tuple(Gs7b9): 75,
       tuple(Amaj): 76, tuple(E): 76, tuple(AoE): 76, tuple(Em7): 76,
       tuple(Am): 76, tuple(Am7G): 76, tuple(DoFs): 78, tuple(G): 74, tuple(Gmaj7Fs): 74, tuple(Em7b): 76,
       tuple(Em7D): 74, tuple(Em11): 78, tuple(EoGs): 80}
chords = [(a, z, c + [TOP[tuple(c)]] if tuple(c) in TOP else c) for a, z, c in chords]

pitches = sorted({p for _, _, c in chords for p in c})
json.dump({'chords': chords, 'pitches': pitches, 'end': END, 'B': B,
           'kick': [blk(1), T_BRIDGE],
           'whispers': [[123.36, 'bebq'], [125.87, 'bbdc'], [127.53, 'bbdc'], [129.76, 'bbdc'], [132.26, 'bbdc'], [134.57, 'bbdc']]},
          open('full/arr.json', 'w'))

# loops: ~11 s "ah" per pitch per pass (the 12-foot tape loop), detuned passes
jobs = []
for p in pitches:
    passes = [('female', 0.0), ('female', 0.06), ('child', 0.0), ('child', -0.05)] if p >= 72 else \
             [('male', 0.0), ('male', 0.07)] if p < 52 else \
             [('male', 0.0), ('male', 0.07), ('female', -0.05), ('female', 0.04)] + ([('child', 0.0)] if p >= 59 else [])
    for body, det in passes:
        name = f'full/loops/p{p}-{body}-{int(det*100):+d}'
        json.dump({'bpm': BPM, 'vibrato': 8, 'lyrics': 'ah', 'notes': [[p + det, 12.5], [0, 1]]}, open(name + '.json', 'w'))
        jobs.append(name)
open('full/loopjobs.txt', 'w').write('\n'.join(jobs) + '\n')
print('lines', len(lines), 'notes', sounding, 'pitches', len(pitches), 'loops', len(jobs))
print('verse1', blk(1), 'chorus1', blk(3), 'instr', blk(7), 'v3', blk(10), 'bridge', T_BRIDGE, 'outro', T_OUT)

# ---- harmonies: diatonic thirds that follow the lead on chosen sections
E_MAJ = {4, 6, 8, 9, 11, 1, 3}; G_MAJ = {7, 9, 11, 0, 2, 4, 6}
def dia(m, steps, scale):
    """Move a midi note by `steps` scale degrees (3rd above = +2, 3rd below = -2)."""
    m = int(round(m)); d = 1 if steps > 0 else -1; k = 0
    if m % 12 not in scale:                     # chromatic note (B#): snap first
        m += d; 
    while k < abs(steps):
        m += d
        if m % 12 in scale: k += 1
    return m
def region(ts):
    if T_BRIDGE <= ts < T_OUT: return 'bridge'
    if ts >= T_OUT: return 'outro'
    for k in (3, 6): 
        if blk(k) <= ts < blk(k + 1): return 'chorus'
    if blk(12) <= ts < T_BRIDGE: return 'chorus'
    for k in (1, 2, 4, 5, 10, 11):
        if blk(k) + 8 * B <= ts < blk(k + 1): return 'lift'
    return None
PARTS = {   # name: (body, steps, regions, octave)
    'hi':    ('female', +2, {'chorus', 'bridge', 'outro'}, 0),
    'lo':    ('male',   -2, {'chorus', 'bridge', 'outro'}, 0),
    'oct':   ('child',   0, {'bridge'}, 12),
    'lift':  ('female', +2, {'lift'}, 0),
}
for name, (body, steps, regs, octv) in PARTS.items():
    hn, hs, t = [], [], 0.0
    for ts, ds, m, sy in events:
        if region(ts) not in regs: continue
        sc = G_MAJ if region(ts) == 'bridge' else E_MAJ
        hm = (dia(m, steps, sc) if steps else int(round(m))) + octv
        if ts > t + 1e-4: hn.append([0, (ts - t) / B])
        hn.append([hm, ds / B]); hs.append(sy); t = ts + ds
    hn.append([0, 1])
    json.dump({'bpm': BPM, 'vibrato': 18, 't0': 0.0, 'syllables': hs, 'notes': hn}, open(f'full/harm-{name}.json', 'w'))
    print('harm', name, body, len(hs), 'notes')
