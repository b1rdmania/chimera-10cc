# Inputs you supply

The scripts need three inputs. They are copyright material, so this repo does not include them.

## 1. Melody and chords: `ht-verse.json`, `ht-chorus.json`, `ht-bridge.json`

Put these in the repo root. `song.py` reads each section's notes in this shape:

```json
{"jsonData": "{\"notes\": [{\"sd\": \"3\", \"octave\": 0, \"beat\": 1.75, \"duration\": 0.25, \"isRest\": false}]}"}
```

- `sd` is the scale degree ("1" to "7", "#7" for the raised seventh).
- `octave` is relative to the tonic octave.
- `beat` starts at 1. `duration` is in beats.
- The verse is in C# minor, the chorus in E major and the bridge in G major. Each section is one 16-beat (verse, chorus) or 32-beat (bridge) block at 67 BPM.

This is the format that Hooktheory's TheoryTab uses. You can also write your own transcription in the same shape.

## 2. Words and timing: `src/official.en.vtt`

Put a WebVTT caption file for the song at `src/official.en.vtt`. `song.py` takes the words from each cue that contains `♪`. It matches each cue to a melody phrase by its timestamp, and uses Chimera's dictionary to split syllables. The timeline follows the 3:45 single edit.

## 3. Whisper text: `inputs/whisper.txt`

Two lines: the first whispered phrase, then the repeated phrase. `render.sh` renders them with the `CHIMERA_WHISPER` switch.
