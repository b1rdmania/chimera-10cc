# I'm Not in Love, sung by one simulated throat

10cc's "I'm Not in Love" (1975), rebuilt with [Chimera](https://github.com/jamesondh/chimera-vocal-synth), the vocal synth by Jameson Hodge. Every sound in the track comes from Chimera. Every face in the video is Chimera's own screen, replaying what the synth sang.

[![The bridge: 32 Chimera voices on the wall](10cc/media/poster.jpg)](https://github.com/b1rdmania/chimera-10cc/releases/download/v1/im-not-in-love-chimera-cut.mp4)

**Watch:** [the 38-second cut](https://github.com/b1rdmania/chimera-10cc/releases/download/v1/im-not-in-love-chimera-cut.mp4) · [the full track, 3:45](https://github.com/b1rdmania/chimera-10cc/releases/download/v1/im-not-in-love-chimera-full.mp4)

**Chimera:** [repo](https://github.com/jamesondh/chimera-vocal-synth) · [try it in the browser](https://chimera.audio)

## Make your own track

Point your coding agent (Claude Code, Codex, Cursor) at this repo and ask for a song:

> Clone github.com/b1rdmania/chimera-10cc, read AGENTS.md, and make me a Chimera track of [your song]. Female lead, a harmony a third above in the chorus, a thick "ooh" choir.

The agent writes one small song file (tempo, key, melody, words, harmonies) and runs `songkit/build.py`. You get an mp3 in about a minute. `AGENTS.md` has the full instructions and the song file format. `songs/example.json` is a short worked example.

You can also run it by hand:

```sh
git clone https://github.com/jamesondh/chimera-vocal-synth
(cd chimera-vocal-synth && cargo build --release -p chimera-cli)
git clone https://github.com/b1rdmania/chimera-10cc && cd chimera-10cc
CHIMERA=../chimera-vocal-synth/target/release/chimera python3 songkit/build.py songs/example.json
```

You need Rust, Python 3 with numpy, and ffmpeg.

## Why this works

Most synths make sounds. Chimera grows a voice: it simulates the lungs, vocal folds, airway and lips, with no samples and no neural audio. That makes it a new instrument.

In 1975, 10cc built a new instrument too. They wanted a choir without a choir or a synth. So they sang every note 16 times, three voices at a time, cut the recordings into long tape loops, and played the loops on the mixing desk faders like keys. That gave 624 voices from three people.

The kit does the same thing with one simulated throat:

- **Lead.** Chimera sings your melody. A quiet, slightly out-of-tune copy plays 12 ms behind it, like 1970s double-tracking.
- **Choir.** One held vowel of about 10 seconds for each chord note, looped like tape. Each note has 2 to 4 copies across male, female and child voices, each a little out of tune. Every loop plays all the time at a low level, because 10cc taped their faders so they never fully closed. A loop comes up when its chord plays.
- **Harmonies.** Extra voices a set number of scale steps from the lead, so they stay in key.
- **Stereo.** Each choir copy sits in its own place from left to right.

## The 10cc track

The full "I'm Not in Love" build adds more on top of the kit: a high choir line, an "ooh" melody in the break, an electric-piano-style fill, a whispered "Big boys don't cry" in Chimera's whisper mode, and a mouth kick. That pipeline is in [10cc/](10cc/). The original recording, lyrics and note transcription are copyright, so they are not included. [10cc/README.md](10cc/README.md) explains what to supply.

## PS: the video

Chimera draws its voice as it sings: the head in cross-section, the airway, the vocal folds, the sound spectrum. It can also save that data frame by frame. The video plays the data back through Chimera's own screens, one face per voice that is actually sounding, from 1 face in the verses to 32 in the bridge. A virtual clock steps the browser one frame at a time, so the picture stays in exact sync with the sound. The scripts and a small Chimera patch are in [10cc/](10cc/).

## Known gaps

- Consonants are softer than a real singer's.
- Auto chords are simple. Give chords by hand for anything richer.
- The 10cc melody comes from a crowd-sourced transcription, so some notes may be off.

## Credits

- [Chimera](https://github.com/jamesondh/chimera-vocal-synth) by Jameson Hodge, MIT.
- "I'm Not in Love" by Eric Stewart and Graham Gouldman, recorded by 10cc, 1975.
- Built by [@b1rdmania](https://github.com/b1rdmania) with Claude Code.

## License

The scripts are MIT. "I'm Not in Love" and its recording belong to their owners.
