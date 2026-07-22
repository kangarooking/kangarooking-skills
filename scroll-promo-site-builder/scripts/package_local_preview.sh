#!/bin/sh
set -eu

usage() {
  echo "Usage: $0 --project DIR --output ARCHIVE.zip [--name FOLDER_NAME]" >&2
  exit 2
}

project=""
output=""
name=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --project) project=$2; shift 2 ;;
    --output) output=$2; shift 2 ;;
    --name) name=$2; shift 2 ;;
    *) usage ;;
  esac
done

[ -n "$project" ] && [ -n "$output" ] || usage
command -v rsync >/dev/null 2>&1 || { echo "rsync not found" >&2; exit 1; }
command -v zip >/dev/null 2>&1 || { echo "zip not found" >&2; exit 1; }
command -v unzip >/dev/null 2>&1 || { echo "unzip not found" >&2; exit 1; }

project=$(cd "$project" && pwd)
[ -n "$name" ] || name=$(basename "$project")
case "$output" in /*) ;; *) output="$(pwd)/$output" ;; esac
mkdir -p "$(dirname "$output")"

temp_root=$(mktemp -d)
trap 'rm -rf "$temp_root"' EXIT HUP INT TERM
stage="$temp_root/$name"
mkdir -p "$stage"

rsync -a \
  --exclude 'node_modules' \
  --exclude '.git' \
  --exclude 'dist' \
  --exclude '.next' \
  --exclude '.wrangler' \
  --exclude '.DS_Store' \
  --exclude '*.log' \
  "$project/" "$stage/"

(cd "$temp_root" && zip -r -q "$output" "$name")
unzip -t "$output" >/dev/null
echo "Wrote $output"
