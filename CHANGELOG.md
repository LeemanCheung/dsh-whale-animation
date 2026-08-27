# Changelog

All notable changes to this project are documented here.

## [0.5.0] - 2026-08-27

### Added

- Restored the first published whale loop as the selectable and playlist-enabled **Classic** state.
- Added Git blob SHA-1 verification for both preserved WebPs and both preserved PNGs.
- Added a shared spine-driven whale model with a rounded melon-shaped head, flexible peduncle, broad flukes, compact pectoral fin, and no dorsal fin.
- Added browser smoke coverage for all seven resolved states.

### Changed

- Restored the v0.3 refined dive loop byte-for-byte as the default **Refined Dive** state.
- Redrew **Sonar**, **Tool Run**, **Stream**, **Calm**, and **Retry** around the new brand-aligned body model.
- Replaced rigid whole-body rotation with a travelling centerline wave so motion propagates through the torso and tail.
- Reworked the retry effect from a cartoon speech bubble to restrained attention rays.
- Expanded the timed playlist to `dive → classic → sonar → work → compose → idle`.
- Updated README visuals, state gallery, animation manifest, validation budgets, and release metadata for v0.5.0.

### Compatibility

- Kept `assets/whale-static.png` as a compatibility alias for pre-v0.4 consumers.
- Preserved the existing semantic status selector, offline runtime, dark-theme behavior, reduced-motion behavior, and lifecycle cleanup.

## [0.4.0] - 2026-08-26

### Added

- Six animation states, a timed and keyword-aware director, per-state PNG fallbacks, deterministic asset generation, browser validation, CI, and automated release packaging.

## [0.3.0] - 2026-08-15

- Refined the original deep-dive loop, README artwork, bundle checks, dark-theme handling, and reduced-motion fallback.
