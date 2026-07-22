#!/bin/zsh
cd "$(dirname "$0")" || exit 1
if ! command -v node >/dev/null 2>&1; then
  echo "Node.js is required. Install the version listed in package.json."
  read -r "?Press Enter to exit."
  exit 1
fi
if [ ! -d node_modules ]; then npm install || exit 1; fi
(sleep 3; open "http://localhost:5173") &
npm run dev
