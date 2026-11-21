# Covers from MIDI

After the 10cc track we made Chimera covers of Enigma's "Sadeness (Part I)", Deep Forest's "Sweet Lullaby", Enya's "Orinoco Flow" and Tallis's "Spem in alium". This folder has the tool and what we learned.

```sh
pip install numpy mido
cd covers/example
CHIMERA=../../../chimera-vocal-synth/target/release/chimera python3 ../midicover.py cover.json
```

`example/` is an original 8-bar tune with a lead, a three-part choir, a hummed bass and drums. It renders in about 30 seconds.

## What we learned

**Take the notes from a MIDI file, not from the record.** The first versions pitch-tracked the record: Demucs split out the stems, then librosa pyin read the pitch. The result was out of tune and you could not recognise the songs. Key and chord checks passed anyway, so they do not catch a wrong melody. A hand-sequenced MIDI file of the song fixed this at once. Someone has usually made one already (bitmidi.com, midis101.com). Use one MIDI track per Chimera part.

**For chant, use GregoBase.** gregobase.selapa.net has Gregorian chant as GABC, with the notes and the Latin together. Enigma sampled real chant recordings, so the monks sing the actual chants (Procedamus in pace, Psalm 24). In GABC with a c3 clef, `h` is do (C4), `i` is D4 and `k` is F4. Download with `download.php?id=<id>&format=gabc&elem=1`. Without `elem=1` the file is empty.

**Respell Latin for Chimera.** Chimera reads English spelling. Write Latin the way it sounds: "pro che dah moos" for "procedamus".

**Put real words on the lead in time.** Do not type the words by hand. Run whisper-cli on the vocal stem from Demucs to get each word's start and end time. The `whisper:` lyric mode splits each word into syllables with `chimera syllables`. Then it walks through the notes in time order: a note gets the next syllable if one starts in it, otherwise it holds the last vowel (`~`). Find the MIDI's tempo and offset against the record first. A grid search of tempo and offset against the pitch track works.

**Make the drums with the same throat.** `chimera render beatbox` makes a kick (`B`), snare (`Pf`), hi-hat (`t`), open hat (`tss`), crash (`kch`) and rimshot (`K`). The tool puts one of these on each hit of the MIDI drum track, so every sound is still Chimera.

**Use several voices for depth.** Each MIDI part can play as several copies, each with its own body, detune, octave and pan. A lush synth pad becomes 6 to 9 voices: male, female and child, a few cents apart. Keep the bass quiet. A hummed bass at full level covers everything else.

**Check the octave.** Some MIDI files put the melody an octave high. Listen once against the record and use `transpose: -12` if needed.

## Config

| Field | Meaning |
|---|---|
| `midi` | The MIDI file, relative to the config. |
| `name` | Output name. Writes `<name>.wav` and `<name>.mp3`. |
| `out` | Folder for the renders. Finished renders are reused, so delete it after you change notes. |
| `bpm` | Optional. Overrides the MIDI's tempo. |
| `parts[].track` | MIDI track number. |
| `parts[].mode` | `mono` sings one line. `poly` splits chords into `k` lines, each sung by its own voice. `spread` spaces them in stereo. |
| `parts[].lyr` | What it sings. `legato:ooh` sings one vowel per phrase. `each:dah` sings one syllable per note. `words:la lu` cycles words. `phrases:line one\|line two` sings one line per phrase. `whisper:<file>\|<bpm>\|<offset>` takes timed words from whisper-cli JSON. |
| `parts[].copies` | `[[body, cents, octave, pan, gain], ...]`. One render per copy. |
| `parts[].bus` | `v` lead (echo, ducks the choir), `c` choir (chorus, long echo), `b` bass (mono, low-pass). |
| `parts[].vib`, `min_d`, `transpose` | Vibrato depth, shortest note kept (beats), semitone shift. |
| `drums.tracks`, `drums.gain` | MIDI drum tracks and their level. General MIDI notes map to the beatbox kit. |
| `fx` | `choir`, `bass`, `drums` levels and `vwet` (lead echo). |

If the words for a part do not give one syllable per note, the tool says so and sings "ah" instead.

## Spem in alium

Tallis wrote "Spem in alium" for 40 voices in 8 choirs. [../spem/](../spem/) sings each of the 40 parts with its own Chimera voice. The notes come from the Brighton Consort MIDI of all 40 parts. Put it at `spem/src/midi/tallis-thomas-spem-in-alium-complete-all-40-parts.mid`, then run `python3 spem/build.py`. The tool guesses where the Latin syllables fall, so some of the underlay is wrong.

## Not included

The MIDI files, stems, Whisper output and lyrics for the covers belong to their owners, so they are not included. Use the tool on files you have.
