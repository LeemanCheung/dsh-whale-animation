#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROME="${CHROME_BIN:-}"
if [[ -z "$CHROME" ]]; then
  for candidate in google-chrome-stable google-chrome chromium chromium-browser; do
    if command -v "$candidate" >/dev/null 2>&1; then CHROME="$(command -v "$candidate")"; break; fi
  done
fi
if [[ -z "$CHROME" ]]; then echo "No Chrome/Chromium binary found" >&2; exit 1; fi

ARTIFACTS="$ROOT/.artifacts"
PROFILE="$ARTIFACTS/chrome-profile"
HTML_URL="file://$ROOT/scripts/browser-smoke.html"
DOM="$ARTIFACTS/browser-smoke-dom.html"
LIGHT="$ARTIFACTS/browser-smoke-light.png"
DARK="$ARTIFACTS/browser-smoke-dark.png"
mkdir -p "$ARTIFACTS"
rm -rf "$PROFILE" "$DOM" "$LIGHT" "$DARK"

FLAGS=(--headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage --disable-background-networking --disable-extensions --no-first-run --allow-file-access-from-files --virtual-time-budget=1500 --user-data-dir="$PROFILE")
timeout 45s "$CHROME" "${FLAGS[@]}" --dump-dom "$HTML_URL" > "$DOM"
grep -q 'data-smoke="dive,classic"' "$DOM"
timeout 45s "$CHROME" "${FLAGS[@]}" --hide-scrollbars --window-size=1000,700 --screenshot="$LIGHT" "$HTML_URL" >/dev/null
timeout 45s "$CHROME" "${FLAGS[@]}" --hide-scrollbars --window-size=1000,700 --screenshot="$DARK" "$HTML_URL?dark=1" >/dev/null
test -s "$LIGHT" && test -s "$DARK"
printf '{"ok":true,"chrome":"%s","states":["dive","classic"],"screenshots":["%s","%s"]}\n' "$CHROME" "$LIGHT" "$DARK"
