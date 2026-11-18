#!/bin/bash
# Render every voice with Chimera, then mix and master.
# Needs: CHIMERA=/path/to/chimera (the patched CLI), python3 with numpy, ffmpeg.
# Inputs (not included, see inputs/README.md): ht-verse.json, ht-chorus.json, ht-bridge.json,
# src/official.en.vtt, inputs/whisper.txt.
set -e
cd "$(dirname "$0")"
: "${CHIMERA:?set CHIMERA to the chimera CLI}"
mkdir -p full/loops fx
python3 song.py                                   # melody, harmonies, chords, loop jobs -> full/

r() { "$CHIMERA" render notes "$1.json" "$1" "$2" --tele "$1.tele" > /dev/null; echo "rendered $1"; }
r full/lead male &  r full/lead-dbl male &
r full/harm-hi female &  r full/harm-lo male &  r full/harm-oct child &  r full/harm-lift female &
r full/ooh-female female &  r full/ooh-child child &
r full/rh-top female &  r full/rh-mid female &  r full/rh-low male &
wait
# tape loops: one held "ah" per pitch per pass; the body is in the file name (p64-female-+4)
xargs -P 6 -I{} sh -c '"$0" render notes {}.json {} $(basename {} | cut -d- -f2) > /dev/null' "$CHIMERA" < full/loopjobs.txt
# mouth kick, and the whisper (needs the CHIMERA_WHISPER switch from patches/chimera-local.patch)
"$CHIMERA" render beatbox fx/kick "B . . . | . . . . | B . . . | . . . ." male 67 4 > /dev/null
CHIMERA_WHISPER=1 "$CHIMERA" render text fx/bebq "$(sed -n 1p inputs/whisper.txt)" female > /dev/null
CHIMERA_WHISPER=1 "$CHIMERA" render text fx/bbdc "$(sed -n 2p inputs/whisper.txt)" female > /dev/null

python3 mix.py && ./master.sh                     # -> not-in-love-full.wav / .mp3
