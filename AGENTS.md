# Making a song with this repo

You are a coding agent. A person wants a song sung entirely by Chimera, the physical-model voice synth. This file tells you how to make it with `songkit/build.py`.

## Setup (once)

1. Clone and build Chimera next to this repo. Stock Chimera is enough for songkit; no patch is needed.

   ```sh
   git clone https://github.com/jamesondh/chimera-vocal-synth ../chimera-vocal-synth
   (cd ../chimera-vocal-synth && cargo build --release -p chimera-cli)
   export CHIMERA=../chimera-vocal-synth/target/release/chimera
   ```

2. Install numpy and ffmpeg (`pip install numpy`, `brew install ffmpeg` or your package manager).

3. Test with the example: `python3 songkit/build.py songs/daisy-bell.json`. It takes under a minute and writes `out/daisy-bell/daisy-bell.mp3`.

## Make a song

1. **Get the song from the person.** You need a melody and words. Ask for the tune, a hummed recording described in notes, sheet music, or a well-known public-domain song. Do not transcribe or reproduce copyrighted lyrics or melodies the person does not own.
2. **Write a song file** in `songs/<name>.json`. Copy `songs/daisy-bell.json` and change it. The fields are below.
3. **Check the syllables.** Run `$CHIMERA syllables "<lyrics>"`. It must give exactly one syllable per sung note. Split words into syllables with spaces ("ba by"). Use `~` to hold the last vowel over an extra note. If a word splits wrong, respell it ("mar ridge", not "mar riage").
4. **Render:** `python3 songkit/build.py songs/<name>.json`.
5. **Give the person the mp3** from `out/<name>/`. Ask what to change, edit the song file and render again. Delete `out/<name>/` before a re-render if you changed the melody or the chords, because finished renders are reused.

## Song file fields

| Field | Meaning |
|---|---|
| `bpm` | Tempo in beats per minute. |
| `beats_per_bar` | 3 for a waltz, 4 for most songs. |
| `key`, `scale` | For example `"B"` and `"major"`, or `"A"` and `"minor"`. Harmonies stay in this key. |
| `intro_bars` | Bars of choir alone before the lead sings. |
| `lead.body` | `male`, `female` or `child`. |
| `lead.octave` | Shift the melody up or down by octaves (`-1` suits a male voice for a melody written high). |
| `lead.notes` | `[[midi, beats], ...]`. MIDI 60 is middle C. A MIDI value of 0 is a rest. |
| `lead.lyrics` | One syllable per sung note, separated by spaces. |
| `chords` | `"auto"` picks one chord per bar from the melody. Or give a list: `[["C", 4], ["Am", 4], ["F", 2], ["G7", 2]]` (name, beats). Qualities: none (major), `m`, `7`, `m7`, `maj7`, `6`, `m6`, `sus4`, `dim`. |
| `harmonies` | A list of extra voices that follow the lead: `steps` is scale steps away (`2` is a third above, `-2` a third below, `4` a fifth above), plus `body`, optional `from_bar`/`to_bar` and `pan` (-1 left to 1 right). |
| `choir.vowel` | What the choir sings: `ah`, `ooh`, `oh`. |
| `choir.passes` | Copies of each choir note (2 to 4). More passes make a thicker choir. |
| `choir.floor_db` | How loud the choir stays between its chords. 10cc used about -24 dB. |
| `double` | `true` adds a quiet double of the lead, 12 ms late. |

## What the script does

- Renders the lead, the double, each harmony and every choir loop with Chimera, all in parallel.
- Builds the choir like 10cc's tape loops. Each loop is about 10 s of one held vowel. Each loop runs all the time at the floor level and rises when its chord plays. Each copy sits at its own place in the stereo field, with a slow random drift, like hands on faders.
- Mixes and masters with ffmpeg: chorus and echo on the choir, presence on the lead, the choir ducking slightly under the lead, loudness to -15 LUFS.

## Limits to tell the person

- Chimera sings English well. It also reads Korean and Russian lyrics (see the Chimera README).
- Consonants are softer than a real singer's.
- Auto chords are simple (one chord per bar from I, IV, V, vi, ii, iii). Give chords by hand for anything richer.
