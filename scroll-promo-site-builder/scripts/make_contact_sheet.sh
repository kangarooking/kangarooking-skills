#!/bin/sh
set -eu

usage() {
  echo "Usage: $0 --project DIR --input DIR --output FILE [--columns N]" >&2
  exit 2
}

project=""
input=""
output=""
columns=4

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project) project=$2; shift 2 ;;
    --input) input=$2; shift 2 ;;
    --output) output=$2; shift 2 ;;
    --columns) columns=$2; shift 2 ;;
    *) usage ;;
  esac
done

[ -n "$project" ] && [ -n "$input" ] && [ -n "$output" ] || usage
command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg not found" >&2; exit 1; }

project=$(cd "$project" && pwd)
case "$input" in /*) ;; *) input="$project/$input" ;; esac
case "$output" in /*) ;; *) output="$project/$output" ;; esac

count=$(find "$input" -maxdepth 1 -type f -iname '*.png' | wc -l | tr -d ' ')
[ "$count" -gt 0 ] || { echo "No images found in $input" >&2; exit 1; }
rows=$(( (count + columns - 1) / columns ))
mkdir -p "$(dirname "$output")"

ffmpeg -loglevel error -y -pattern_type glob -i "$input/*.png" \
  -vf "scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2:color=white,tile=${columns}x${rows}:padding=8:margin=8" \
  -frames:v 1 "$output"
echo "Wrote $output"
