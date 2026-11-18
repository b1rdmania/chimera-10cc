#!/bin/bash
# Join the silent segments (segs/a,b,c.mp4: song time 0–75, 75–150, 150–225) and lay the song under them.
set -e
cd "$(dirname "$0")/.."
printf "file 'a.mp4'\nfile 'b.mp4'\nfile 'c.mp4'\n" > segs/list.txt
ffmpeg -y -loglevel error -f concat -safe 0 -i segs/list.txt -i ../not-in-love-full.wav -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 320k -shortest -movflags +faststart not-in-love-merged-full.mp4
ffmpeg -y -loglevel error -i not-in-love-merged-full.mp4 -c:v libx264 -preset slow -crf 22 -pix_fmt yuv420p -c:a aac -b:a 192k \
  -movflags +faststart not-in-love-merged-full-post.mp4
for f in not-in-love-merged-full.mp4 not-in-love-merged-full-post.mp4; do
  ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames,duration -show_entries format=size -of compact $f; done
