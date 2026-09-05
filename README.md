# NOCTURNE / 夜曲

Three interactive chrome sculptures: Ligature, Aperture, Afterimage.

## Run

```sh
node server.mjs
```

Open http://localhost:3000. The deployed site serves Three.js r180 from its own `vendor/` directory. A native WebGL adapter provides the same shader when a module cannot load.

## Mobile

A dedicated stage separates sculpture, caption and controls. Visual viewport height and device safe areas drive placement. All visible phone controls are at least 44 × 44 CSS pixels. Portrait, landscape and tablet layouts are distinct. Drag horizontally to rotate, hold to deconstruct, and swipe vertically or tap a chapter to change the work. Pinch zoom is preserved. Export opens a poster preview on touch devices, with download and optional native sharing.

## Source and publishing

This independent `nocturne-site` branch does not modify the original repository's `main` branch or any plugin release. Source files, vendor files and tests belong only to this web artwork. No analytics, accounts, API keys, external fonts or remote textures are used. The workflow installs pinned Three.js r180, runs browser checks, and commits the tested static assets. Public access is provided by the GitHack static CDN, not GitHub Pages. GitHack may show its repository confirmation screen on the first visit.

## Controls

Drag: rotate. Hold / D: deconstruct. Scroll / 1 2 3: chapter. Space: pause. H: focus view. F: fullscreen when supported. Double click: reset angle.

## Tests

`tests/browser_checks.py` runs layout, renderer, controls, touch, export and resize checks against Chromium and WebKit. These are browser-engine tests, not physical iPhone tests. CI results and screenshots are stored as workflow artifacts.
