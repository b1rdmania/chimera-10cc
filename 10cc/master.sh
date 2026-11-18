#!/bin/bash
set -e
cd "$(dirname "$0")/full"
R="-f f32le -ar 48000 -ac 1"
ffmpeg -y -loglevel error $R -i stem-padL.f32 $R -i stem-padR.f32 $R -i stem-lead.f32 $R -i stem-kick.f32 $R -i stem-wh.f32 $R -i stem-hiss.f32 $R -i stem-harmL.f32 $R -i stem-harmR.f32 $R -i stem-fillL.f32 $R -i stem-fillR.f32 -filter_complex "\
[0]volume=${PG:-0.22},chorus=0.6:0.9:40|55|70:0.4|0.35|0.3:0.25|0.3|0.4:2|2.5|3,lowpass=f=4500,aecho=0.8:0.85:110|230|410|690:0.45|0.35|0.25|0.18,equalizer=f=2000:t=q:w=1.0:g=-4[pl];\
[1]volume=${PG:-0.22},chorus=0.6:0.9:45|62|77:0.4|0.35|0.3:0.3|0.27|0.45:2.2|2.7|3.3,lowpass=f=4500,aecho=0.8:0.85:135|265|455|740:0.45|0.35|0.25|0.18,equalizer=f=2000:t=q:w=1.0:g=-4[pr];\
[pl][pr]join=inputs=2:channel_layout=stereo[pads0];\
[2]volume=${LG:-0.9},highpass=f=90,equalizer=f=3200:t=q:w=1.2:g=3,aecho=0.8:0.6:180|360:0.14|0.07,pan=stereo|c0=c0|c1=c0,asplit=2[lds][ldk];\
[pads0][ldk]sidechaincompress=threshold=0.04:ratio=2.5:attack=15:release=250:makeup=1[pads];\
[3]volume=2.6,lowpass=f=140,pan=stereo|c0=c0|c1=c0[kks];\
[4]volume=2.2,highpass=f=300,aecho=0.8:0.8:90|210|400:0.5|0.35|0.2,pan=stereo|c0=0.9*c0|c1=0.5*c0[wh];\
[5]pan=stereo|c0=c0|c1=c0[hs];\
[6][7]join=inputs=2:channel_layout=stereo,volume=${HG:-0.7},highpass=f=120,aecho=0.8:0.75:150|310|520:0.35|0.25|0.15[hm];\
[8][9]join=inputs=2:channel_layout=stereo,volume=${FG:-0.5},highpass=f=150,equalizer=f=1800:t=q:w=1.2:g=2,aecho=0.8:0.6:200|380:0.18|0.1[fl];\
[pads][lds][kks][wh][hs][hm][fl]amix=inputs=7:normalize=0,loudnorm=I=-15:TP=-1.2:LRA=11[out]" -map "[out]" -ar 44100 ../${OUT:-not-in-love-full}.wav
cd ..
[ -z "$OUT" ] && ffmpeg -y -loglevel error -i not-in-love-full.wav -b:a 256k not-in-love-full.mp3 || true
