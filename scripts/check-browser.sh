#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROME="${CHROME_BIN:-}"
if [[ -z "$CHROME" ]]; then
  for candidate in google-chrome-stable google-chrome chromium chromium-browser; do
    if command -v "$candidate" >/dev/null 2>&1; then
      CHROME="$(command -v "$candidate")"
      break
    fi
  done
fi
if [[ -z "$CHROME" ]]; then
  echo "No Chrome/Chromium binary found" >&2
  exit 1
fi

ARTIFACTS="$ROOT/.artifacts"
PROFILE="$ARTIFACTS/chrome-profile"
HTML_URL="file://$ROOT/scripts/browser-smoke.html"
DOM="$ARTIFACTS/browser-smoke-dom.html"
SCREENSHOT="$ARTIFACTS/browser-smoke-light.png"
DARK_SCREENSHOT="$ARTIFACTS/browser-smoke-dark.png"
mkdir -p "$ARTIFACTS"
rm -rf "$PROFILE" "$DOM" "$SCREENSHOT" "$DARK_SCREENSHOT"

COMMON_FLAGS=(
  --headless=new
  --no-sandbox
  --disable-gpu
  --disable-dev-shm-usage
  --disable-background-networking
  --disable-component-update
  --disable-default-apps
  --disable-extensions
  --disable-sync
  --metrics-recording-only
  --mute-audio
  --no-first-run
  --no-default-browser-check
  --allow-file-access-from-files
  --virtual-time-budget=1500
  --user-data-dir="$PROFILE"
)

timeout 45s "$CHROME" "${COMMON_FLAGS[@]}" --dump-dom "$HTML_URL" > "$DOM"
grep -q 'data-smoke="dive,classic,sonar,work,compose,idle,alert"' "$DOM"

timeout 45s "$CHROME" "${COMMON_FLAGS[@]}" \
  --hide-scrollbars \
  --window-size=1200,1080 \
  --screenshot="$SCREENSHOT" \
  "$HTML_URL" >/dev/null

timeout 45s "$CHROME" "${COMMON_FLAGS[@]}" \
  --hide-scrollbars \
  --window-size=1200,1080 \
  --screenshot="$DARK_SCREENSHOT" \
  "$HTML_URL?dark=1" >/dev/null

test -s "$SCREENSHOT"
test -s "$DARK_SCREENSHOT"
printf '{"ok":true,"chrome":"%s","states":["dive","classic","sonar","work","compose","idle","alert"],"screenshots":["%s","%s"]}\n' "$CHROME" "$SCREENSHOT" "$DARK_SCREENSHOT"
