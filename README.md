# I'm Not in Love, one simulated throat

These scripts rebuild 10cc's "I'm Not in Love" (1975) with [Chimera](https://github.com/jamesondh/chimera-vocal-synth), a physical-model voice synth. Chimera simulates the lungs, vocal folds, airway and lips. It uses no samples and no neural audio.

Every sound in the track comes from Chimera. The video shows Chimera's own instrument screens, which replay the telemetry the synth recorded while it sang.

## What is in the track

- **Lead.** One male voice sings the melody from a note transcription. A second, slightly detuned copy plays 12 ms late, the way 1970s double-tracking worked.
- **Choir.** 10cc made their choir from tape loops of their own voices: 16 passes of 3 voices on each note, played on the mixing desk faders. The scripts do the same. Each pitch is one held "ah" of about 10 s. Each pitch has 2 to 5 detuned passes across male, female and child bodies. The loops run all the time at -24 dB, as 10cc's taped faders did. A fader brings a loop up when its chord plays.
- **Choir top line.** A high female and child line follows the chords, about an octave above the bed.
- **Harmonies.** Diatonic thirds above and below the lead in the choruses, the bridge and the outro.
- **Break.** An "ooh" melody, transcribed from the original.
- **Fill.** A hummed, electric-piano-style figure at the end of each verse half. It auto-pans at 5 Hz.
- **Whisper.** "Big boys don't cry" uses Chimera's unvoiced mode, so the vocal folds do not vibrate.
- **Kick.** Chimera's beatbox mouth.
- **Stereo.** Each loop has its own position across the stereo field. The width was measured against the original.

## What is not included

The original recording, the lyrics and the note transcription are copyright material. This repo does not include them. You supply them yourself. See [inputs/README.md](inputs/README.md) for the formats.

## Requirements

- macOS or Linux, Rust (stable), Bun, Python 3 with numpy, ffmpeg, Node with Playwright.
- A clone of Chimera with the patch in `patches/` applied.

## Steps

1. **Build Chimera with the patch.**

   ```sh
   git clone https://github.com/jamesondh/chimera-vocal-synth
   cd chimera-vocal-synth
   git checkout $(cat ../chimera-10cc-recipe/patches/BASE_COMMIT)
   git apply ../chimera-10cc-recipe/patches/chimera-local.patch
   cargo build --release -p chimera-cli
   bun install
   ```

   The patch adds two things: a `CHIMERA_WHISPER` switch for the text renderer, and hidden replay routes that make the app's screens play back recorded telemetry.

2. **Add your inputs.** Put them where [inputs/README.md](inputs/README.md) says.

3. **Render and mix the track.**

   ```sh
   cd chimera-10cc-recipe
   CHIMERA=../chimera-vocal-synth/target/release/chimera ./render.sh
   ```

   This writes `not-in-love-full.wav` and `.mp3`. The renders take about 10 to 20 minutes on an M-series Mac.

4. **Make the video.**

   ```sh
   npm install && npx playwright install chromium          # browser for the frame capture
   python3 film/env.py                                     # measured loudness per track
   CHIMERA_REPO=../chimera-vocal-synth python3 film2/tools/prep3.py --render
   (cd ../chimera-vocal-synth && bun run dev) &            # serves the app on 127.0.0.1:5317
   mkdir -p film2/segs
   node film2/tools/cap3.mjs video 0 75 film2/segs/a.mp4   # capture the wall, song time 0-75 s
   node film2/tools/cap3.mjs video 75 150 film2/segs/b.mp4
   node film2/tools/cap3.mjs video 150 225 film2/segs/c.mp4
   ./film2/tools/assemble.sh                               # join the segments and add the song
   ```

   The capture runs on a virtual clock, so the picture is in exact sync with the audio. Each segment takes about 4 minutes. The wall layout changes on the song's phrases. Each face replays the telemetry of one voice that sounds at that moment, from 1 face in the verses to 32 in the bridge.

## Known limits

- The melody comes from a crowd-sourced transcription. Some notes can be wrong.
- The fill was transcribed from separated stems. It was not checked by ear.
- Some consonants are soft. Chimera's plosives are quiet, and the choir can mask them.
- The app patch is a local hack for this film. It is not a Chimera feature.

## Credits

- Chimera is by Jameson Hodge (MIT).
- "I'm Not in Love" is by Eric Stewart and Graham Gouldman, recorded by 10cc in 1975.

## License

The scripts in this repo are MIT. The song and recording belong to their owners.
