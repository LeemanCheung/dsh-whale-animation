# dsh-whale-animation

Two original whale animations for DeepSeek Harness Web. Nothing else.

| Refined Dive | Classic |
|---|---|
| <img src="assets/whale-dive.webp" alt="Refined Dive" width="180" /> | <img src="assets/whale-classic.webp" alt="Classic" width="180" /> |

## Scope

- **Refined Dive**: restored from commit `65e1205d1fbf4b01997e6dfc099103b0f9717e37`.
- **Classic**: restored from first-published commit `95b06e3f0e6ea817d25858eb29f7064a233b3c65`.
- Both animated WebPs and both reduced-motion PNGs are verified by Git blob SHA-1, SHA-256, frame count, and timing.
- The timed director alternates `dive → classic` every 11 seconds. Explicit classic/original wording selects Classic immediately; thinking/reasoning wording selects Dive.
- Dark theme, 84/72/60 px responsive sizing, reduced-motion PNGs, offline embedding, and lifecycle cleanup remain supported.

Removed in v0.7.0: Spout, Sonar, Tool Run, Stream, Calm, Retry, all generated art sources, and their build pipeline.

## Install

```powershell
dsh plugin --profile web add github:LeemanCheung/dsh-whale-animation
```

Restart DSH or hard-refresh DSH Web after upgrading.

## Verify

```powershell
npm run verify
npm run check:browser
npm pack --dry-run
```

`npm run verify` regenerates only `assets/manifest.json` and `lib/client.js`; it never regenerates or re-encodes either original animation.

## Runtime contract

| Property | Refined Dive | Classic |
|---|---:|---:|
| Canvas | 352 × 352 | 184 × 184 |
| Frames | 60 | 618 |
| Frame duration | 33 ms | 17 ms |
| Loop duration | 1.980 s | 10.506 s |
| Source | byte-preserved | byte-preserved |

The plugin is independent and is not affiliated with or endorsed by DeepSeek. See [NOTICE.md](NOTICE.md).

English · [简体中文](README.zh-CN.md)
