#!/usr/bin/env bash
set -euo pipefail

# Reset top-level files from bundle/ canonical copies.
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLE_DIR="$ROOT_DIR/bundle"

copy_file() {
  local src="$1" dest="$2"
  if [[ -f "$src" ]]; then
    cp "$src" "$dest"
    echo "Copied $src -> $dest"
  else
    echo "Warning: missing $src" >&2
  fi
}

copy_file "$BUNDLE_DIR/app.py" "$ROOT_DIR/app.py"
copy_file "$BUNDLE_DIR/app_utils.py" "$ROOT_DIR/app_utils.py"
copy_file "$BUNDLE_DIR/requirements.txt" "$ROOT_DIR/requirements.txt"
copy_file "$BUNDLE_DIR/README.md" "$ROOT_DIR/README.md"
mkdir -p "$ROOT_DIR/data"
copy_file "$BUNDLE_DIR/data/arima_sample.csv" "$ROOT_DIR/data/arima_sample.csv"

echo "Done. Review changes with 'git status' and commit as needed."
