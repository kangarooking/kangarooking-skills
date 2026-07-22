#!/usr/bin/env bash
set -eu

usage() {
  echo "Usage: $0 --project DIR [--input DIR] --output DIR [--head SEC] [--tail SEC]" >&2
  exit 2
}

project=""
input="assets/video"
output=""
head_offset="0.15"
tail_offset="0.15"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project) project=$2; shift 2 ;;
    --input) input=$2; shift 2 ;;
    --output) output=$2; shift 2 ;;
    --head) head_offset=$2; shift 2 ;;
    --tail) tail_offset=$2; shift 2 ;;
    *) usage ;;
  esac
done

[ -n "$project" ] && [ -n "$output" ] || usage
command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg not found" >&2; exit 1; }
command -v ffprobe >/dev/null 2>&1 || { echo "ffprobe not found" >&2; exit 1; }

project=$(cd "$project" && pwd)
case "$input" in /*) ;; *) input="$project/$input" ;; esac
case "$output" in /*) ;; *) output="$project/$output" ;; esac
[ -d "$input" ] || { echo "Input directory not found: $input" >&2; exit 1; }
mkdir -p "$output"

find -L "$input" -type f \( -iname '*.mp4' -o -iname '*.mov' -o -iname '*.m4v' -o -iname '*.webm' \) -print0 |
while IFS= read -r -d '' video; do
  base=$(basename "$video")
  stem=${base%.*}
  duration=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$video")
  tail_time=$(awk -v d="$duration" -v t="$tail_offset" 'BEGIN { x=d-t; if (x<0) x=0; printf "%.3f", x }')
  ffmpeg -nostdin -loglevel error -y -ss "$head_offset" -i "$video" -frames:v 1 "$output/${stem}-start.png"
  ffmpeg -nostdin -loglevel error -y -ss "$tail_time" -i "$video" -frames:v 1 "$output/${stem}-end.png"
  echo "Extracted $stem"
done
