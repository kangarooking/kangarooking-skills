#!/bin/sh
set -eu

usage() {
  echo "Usage: $0 --project DIR --input FILE --output FILE [--width N] [--height N] [--fps N] [--crf N] [--gop N]" >&2
  exit 2
}

project=""
input=""
output=""
width=1280
height=720
fps=30
crf=23
gop=8

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project) project=$2; shift 2 ;;
    --input) input=$2; shift 2 ;;
    --output) output=$2; shift 2 ;;
    --width) width=$2; shift 2 ;;
    --height) height=$2; shift 2 ;;
    --fps) fps=$2; shift 2 ;;
    --crf) crf=$2; shift 2 ;;
    --gop) gop=$2; shift 2 ;;
    *) usage ;;
  esac
done

[ -n "$project" ] && [ -n "$input" ] && [ -n "$output" ] || usage
command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg not found" >&2; exit 1; }

project=$(cd "$project" && pwd)
case "$input" in /*) ;; *) input="$project/$input" ;; esac
case "$output" in /*) ;; *) output="$project/$output" ;; esac
mkdir -p "$(dirname "$output")"

ffmpeg -loglevel error -y -i "$input" -an \
  -vf "scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2:color=black,fps=${fps}" \
  -c:v libx264 -preset slow -crf "$crf" -pix_fmt yuv420p \
  -g "$gop" -keyint_min "$gop" -sc_threshold 0 -movflags +faststart "$output"
echo "Wrote $output"
