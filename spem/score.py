"""Parse the 40 voice tracks of the Brighton Consort / David Siu Spem MIDI, and set the Latin underlay."""
import mido
MIDI = 'src/midi/tallis-thomas-spem-in-alium-complete-all-40-parts.mid'
VOICES = ['treble', 'mean', 'alto', 'tenor', 'bass']

def parse(path=MIDI):
    m = mido.MidiFile(path); tpb = m.ticks_per_beat; parts = []
    for ti in range(1, 41):
        tt = 0; on = {}; out = []
        for x in m.tracks[ti]:
            tt += x.time
            if x.type == 'note_on' and x.velocity > 0: on[x.note] = tt
            elif x.type in ('note_off', 'note_on') and x.note in on:
                s = on.pop(x.note); out.append((s / tpb, (tt - s) / tpb, x.note))
        out.sort()
        parts.append({'choir': (ti - 1) // 5 + 1, 'voice': VOICES[(ti - 1) % 5], 'notes': out})
    return parts

# Latin text as IPA-ish units Chimera's phoneme set knows: (onset, nucleus, coda, word_end, phrase_end)
def S(on, nu, co='', we=True, pe=False): return (on.split() if on else [], nu, co.split() if co else [], we, pe)
TEXT = [
 S('s p','ɛ','m'), S('','ɪ','n'), S('','ɑ',we=False), S('l','i',we=False), S('','u','m'),
 S('n','u','n',False), S('kw','ɑ','m'), S('h','ɑ',we=False), S('b','u',we=False), S('','i',pe=True),
 S('p ɹ','eɪ',we=False), S('t','ɛ','ɹ'), S('','ɪ','n'), S('t','eɪ'),
 S('d','eɪ',we=False), S('','u','s'), S('','ɪ','s',False), S('ɹ','ɑ',we=False), S('','ɛ','l',pe=True),
 S('kw','i'), S('','ɪ',we=False), S('ɹ','ɑ',we=False), S('s k','eɪ',we=False), S('ɹ','i','s'),
 S('','ɛ','t'), S('p ɹ','oʊ',we=False), S('p','i',we=False), S('t','i',we=False), S('','u','s'),
 S('','eɪ',we=False), S('ɹ','i','s',pe=True),
 S('','ɛ','t'), S('','ɔ',we=False), S('m n','i',we=False), S('','ɑ'),
 S('p','ɛ','k',False), S('k','ɑ',we=False), S('t','ɑ'), S('h','oʊ',we=False), S('m','i',we=False), S('n','u','m'),
 S('','ɪ','n'), S('t ɹ','i',we=False), S('b','u',we=False), S('l','ɑ',we=False), S('t','i',we=False), S('','oʊ',we=False), S('n','eɪ'),
 S('d','i',we=False), S('m','ɪ','t',False), S('t','ɪ','s',pe=True),
 S('d','oʊ',we=False), S('m','i',we=False), S('n','eɪ'), S('d','eɪ',we=False), S('','u','s',pe=True),
 S('k ɹ','eɪ',we=False), S('','ɑ',we=False), S('t','ɔ','ɹ'), S('tʃ','eɪ',we=False), S('l','i'),
 S('','ɛ','t'), S('t','ɛ','ɹ',False), S('ɹ','eɪ',pe=True),
 S('ɹ','eɪ',we=False), S('s p','i',we=False), S('tʃ','eɪ'), S('','u',we=False), S('m','i',we=False), S('l','i',we=False), S('t','ɑ',we=False), S('t','ɛ','m'),
 S('n','oʊ',we=False), S('s t ɹ','ɑ','m',pe=True),
]
WORDS = ['spem','in','alium','nunquam','habui','praeter','in','te','Deus','Israel','qui','irasceris','et','propitius','eris',
 'et','omnia','peccata','hominum','in','tribulatione','dimittis','Domine','Deus','Creator','caeli','et','terrae','respice','humilitatem','nostram']
L = len(TEXT)

def fold(notes):
    """Group notes into syllable slots. Returns list of (first_idx, [continuation idx])."""
    groups = []; i = 0; n = len(notes)
    while i < n:
        j = i + 1
        # run of 3+ short joined notes: first carries the syllable, the rest are melisma
        k = i
        while k + 1 < n and notes[k][1] <= 1.0 and notes[k + 1][1] <= 1.0 and notes[k + 1][0] - (notes[k][0] + notes[k][1]) < 0.01: k += 1
        if k - i >= 2 and notes[i][1] <= 1.0: j = k + 1
        groups.append((i, list(range(i + 1, j)))); i = j
    return groups

def underlay(notes):
    """Return a list of per-note syllable objects (dicts for Chimera's 'syllables' array); notes are (start,dur,midi)."""
    # phrases split at gaps >= 1 beat
    phrases = [[0]]
    for i in range(1, len(notes)):
        if notes[i][0] - (notes[i - 1][0] + notes[i - 1][1]) >= 1.0: phrases.append([])
        phrases[-1].append(i)
    slots = [fold([notes[i] for i in ph]) for ph in phrases]
    INF = 1e9; P = len(phrases)
    cost = [[INF] * L for _ in range(P + 1)]; back = [[None] * L for _ in range(P + 1)]
    cost[0][0] = 0
    for i in range(P):
        n = len(slots[i])
        for p in range(L):
            if cost[i][p] >= INF: continue
            for s in range(1, n + 1):
                q = (p + s) % L; last = TEXT[(p + s - 1) % L]
                c = cost[i][p] + (0 if last[3] else 4) - (0.6 if last[4] else 0) + 0.45 * (n - s) + (0.8 if s == 1 and n > 2 else 0)
                if p + s > 2 * L and False: pass
                if c < cost[i + 1][q]: cost[i + 1][q] = c; back[i + 1][q] = (p, s)
    # prefer finishing at the end of the text
    q = min(range(L), key=lambda q: cost[P][q] + (0 if q == 0 else 3))
    take = [0] * P
    for i in range(P, 0, -1):
        p, s = back[i][q]; take[i - 1] = (p, s); q = p
    sylls = [None] * len(notes)
    for i, ph in enumerate(phrases):
        p, s = take[i]; gs = slots[i]; n = len(gs)
        # which slots become extra melisma: shortest non-first ones
        drop = set(sorted(range(1, n), key=lambda g: notes[ph[gs[g][0]]][1])[:n - s]) if n > s else set()
        t = p; prev = None
        for g, (first, rest) in enumerate(gs):
            idxs = [ph[first]] + [ph[r] for r in rest]
            if g in drop and prev is not None:
                for ix in idxs: sylls[ix] = ('~', prev)
                continue
            u = TEXT[t % L]; t += 1; prev = u
            sylls[idxs[0]] = ('s', u)
            for ix in idxs[1:]: sylls[ix] = ('~', u)
    return sylls

def to_chimera(notes, sylls):
    """Move each syllable's coda to its last melisma note; return Chimera syllable objects."""
    out = [None] * len(notes); last = {}
    cur = None
    for i, (kind, u) in enumerate(sylls):
        if kind == 's': cur = i
        last[cur] = i
    cur = None
    for i, (kind, u) in enumerate(sylls):
        on, nu, co, we, pe = u
        has_cont = False
        if kind == 's': cur = i
        end = last[cur] == i
        j = lambda l: [{'ipa': x, 'stress': 0} for x in l]
        o = {'text': '~' if kind == '~' else '', 'onset': j(on) if kind == 's' else [], 'nucleus': {'ipa': nu, 'stress': 1},
             'coda': j(co) if end else [], 'wordEnd': bool(we and end), 'phraseEnd': bool(pe and end)}
        if kind == '~': o['melisma'] = True
        out[i] = o
    return out
