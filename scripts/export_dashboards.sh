#!/usr/bin/env bash
# Export Streamlit dashboards to static HTML for the info site.
# Usage: scripts/export_dashboards.sh [source_dir]
# Default source_dir is 'pages'.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${1:-$ROOT_DIR/pages}"
DEST_DIR="$ROOT_DIR/docs/dashboards"

mkdir -p "$DEST_DIR"

for app in "$SRC_DIR"/*.py; do
  [ -e "$app" ] || continue
  name=$(basename "${app%.py}")
  tmpdir=$(mktemp -d)
  echo "Exporting $app"
  streamlit static "$app" -o "$tmpdir"
  mv "$tmpdir"/index.html "$DEST_DIR/$name.html"
  rm -rf "$tmpdir"

done

echo "Dashboards exported to $DEST_DIR"
