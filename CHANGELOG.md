# Changelog

All notable changes to this project are documented here.

## [0.4.0] - 2026-08-26

### Added

- Six original monochrome animation states: **Deep Dive**, **Sonar**, **Tool Run**, **Stream**, **Calm**, and **Retry**.
- A five-state timed animation director that rotates every 9 seconds while the current Harness UI keeps displaying `Deep diving...`.
- Keyword overrides for future or customized status labels in English and Chinese.
- A state-specific PNG fallback for every animation when `prefers-reduced-motion: reduce` is enabled.
- Deterministic Pillow asset generation, an asset manifest with SHA-256 checksums, a state gallery, and a multi-state README preview.
- Pull-request CI and an automatic GitHub release workflow tied to package-version changes on `main`.

### Changed

- Replaced the single fixed animation with a manifest-driven client bundle.
- Tightened the DOM target to the turn status' semantic `role="status"` selector plus the current hashed-class compatibility selector.
- Stopped clearing the host's `::before`; the plugin now owns only `::after`.
- Added responsive 84 / 72 / 60 px presentation rules and per-state transition keyframes.
- Expanded validation to cover all WebP frame timings, PNG signatures, manifest hashes, embedded data URLs, state resolution, timed rotation, reduced-motion behavior, and lifecycle cleanup.

### Removed

- The obsolete single `assets/whale-static.png` fallback and the old three-frame screenshot gallery.

## [0.3.0] - 2026-08-15

- Refined the original 60-frame deep-dive loop, README artwork, bundle checks, dark-theme handling, and reduced-motion fallback.
