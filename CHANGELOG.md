# Changelog

## [0.7.1] - 2026-09-05

### Fixed

- Removed the unused legacy client-runtime injection, which is no longer provided by DSH 0.1.2-rc.1.
- Canonicalized generated JavaScript to LF so Windows and Linux reproduce the same committed client. CI now verifies both platforms.
- Paused document polling in background tabs and verified visibility resume and hot-reload cleanup.
- Replaced the arbitrary 11-second cut with the assets' exact loop durations. Status-driven changes wait for the current loop to finish.
- Gave each newly selected animation a disposable local image URL so it starts from its own first frame instead of sharing another element's playback position.
- Respected an explicitly selected light DSH theme even when the operating system prefers dark mode.

### Preserved

- The two original Dive and Classic raster animations, their exact bytes and playback timings, and all theme and reduced-motion behavior.

## [0.7.0] - 2026-08-31

### Changed

- Reduced the plugin to the two original byte-preserved animations: Refined Dive and Classic.
- Removed Spout, Sonar, Tool Run, Stream, Calm, Retry, generated artwork, generation dependencies, and all non-original runtime assets.
- Reduced the director, manifest, tests, browser fixture, package, CI, and documentation to the two-state contract.

### Preserved

- Refined Dive WebP/PNG Git blobs from `65e1205d1fbf4b01997e6dfc099103b0f9717e37`.
- Classic WebP/PNG Git blobs from `95b06e3f0e6ea817d25858eb29f7064a233b3c65`.
