# The 10cc pipeline

This folder rebuilds the full "I'm Not in Love" track and its video. For your own songs, use [songkit](../AGENTS.md) instead.

## What you supply

The original recording, the lyrics and the note transcription are copyright, so they are not here. [INPUTS.md](INPUTS.md) shows the formats.

## Steps

Run these from this folder.

1. **Build Chimera with the patch.** The patch adds a whisper switch for the text renderer and the playback screens for the video.

   ```sh
   git clone https://github.com/jamesondh/chimera-vocal-synth ../../chimera-vocal-synth
   cd ../../chimera-vocal-synth
   git checkout $(cat ../chimera-10cc/10cc/patches/BASE_COMMIT)
   git apply ../chimera-10cc/10cc/patches/chimera-local.patch
   cargo build --release -p chimera-cli && bun install
   cd ../chimera-10cc/10cc
   ```

2. **Make the track** (10 to 20 minutes, writes `not-in-love-full.wav`):

   ```sh
   CHIMERA=../../chimera-vocal-synth/target/release/chimera ./render.sh
   ```

3. **Make the video** (each capture step takes about 4 minutes):

   ```sh
   npm install && npx playwright install chromium
   python3 film/env.py
   CHIMERA_REPO=../../chimera-vocal-synth python3 film2/tools/prep3.py --render
   (cd ../../chimera-vocal-synth && bun run dev) &
   mkdir -p film2/segs
   node film2/tools/cap3.mjs video 0 75 film2/segs/a.mp4
   node film2/tools/cap3.mjs video 75 150 film2/segs/b.mp4
   node film2/tools/cap3.mjs video 150 225 film2/segs/c.mp4
   ./film2/tools/assemble.sh
   ```

## Known gaps

- The fill was worked out from separated audio, not checked by ear.
- The patch is a quick local change for this video, not a Chimera feature.
- This pipeline has run on one machine. Expect some first-run friction.
