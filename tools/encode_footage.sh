#!/bin/bash
# encode_footage.sh <prefix> <out.mp4> : 320x240 raw frames + 44744 Hz audio -> 960x720 H.264/AAC, crisp pixels
set -e
ffmpeg -y -loglevel error -f rawvideo -pix_fmt rgb24 -s 320x240 -framerate 60 -i "$1.rgb" \
       -f s16le -ar 44744 -ac 2 -i "$1.s16" \
       -vf "scale=960:720:flags=neighbor,format=yuv420p" -c:v libx264 -preset slow -crf 16 \
       -c:a aac -b:a 192k -ar 48000 -shortest -movflags +faststart "$2"
