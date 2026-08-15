<p align="center">
  <img src="docs/hero.png" alt="dsh-whale-animation — a seamless whale-dive status animation for DeepSeek Harness" width="100%" />
</p>

<p align="center">
  <a href="https://awesome.re"><img src="https://awesome.re/badge.svg" alt="Awesome" /></a>
  <a href="https://awesome-dsh-plugin.com"><img src="https://awesome-dsh-plugin.com/badge.svg" alt="Awesome DSH Plugin" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2563eb.svg" alt="MIT license" /></a>
  <img src="https://img.shields.io/badge/DSH-Web-0f172a.svg" alt="DeepSeek Harness Web" />
  <img src="https://img.shields.io/badge/runtime-offline-0f766e.svg" alt="Offline at runtime" />
  <img src="https://img.shields.io/badge/motion-reduced--motion%20ready-7c3aed.svg" alt="Reduced-motion ready" />
</p>

<p align="center">
  <strong>A persistent black whale-dive animation beside the DeepSeek Harness turn status.</strong><br />
  Closed-loop playback, no runtime network requests, and a static fallback for reduced-motion users.
</p>

<p align="center">
  English · <a href="README.zh-CN.md">简体中文</a>
</p>

## Preview

<p align="center">
  <img src="docs/preview.webp" alt="Animated preview of the whale beside the Deep diving status" width="900" />
</p>

> The preview preserves all **60 native image-2 drawings** and their production timing; no extra in-between frames are inserted. v0.3.0 locks a compact head, lifted snout, eye, mouth and short fluke while keeping the torso and tail articulated frame by frame.

## Screenshots

<table>
  <tr>
    <td width="33%"><img src="docs/screenshots/launch.png" alt="The whale breaching the waterline" /></td>
    <td width="33%"><img src="docs/screenshots/apex.png" alt="The whale curling at the leap apex" /></td>
    <td width="33%"><img src="docs/screenshots/deep-dive.png" alt="The whale returning below the surface" /></td>
  </tr>
  <tr>
    <td align="center"><strong>01 — Breach</strong></td>
    <td align="center"><strong>02 — Apex</strong></td>
    <td align="center"><strong>03 — Deep dive</strong></td>
  </tr>
</table>

Each screenshot is rendered from the committed `assets/whale-dive.webp`, so the gallery represents the frames users actually receive—not separate concept art.

## Highlights

| | Feature | What it means |
|---|---|---|
| 🌊 | **Propagating water surface** | Breach and entry generate outward-travelling crests, recoil and damped settling instead of a frozen waterline. |
| 🐋 | **Stable original whale identity** | The compact head, lifted snout, eye and short fluke stay consistent while the torso follows head-led, tail-lagged flexion. |
| 📦 | **Self-contained bundle** | Animated WebP and PNG fallback are embedded in the built client; no runtime URL or source-frame directory is required. |
| ♿ | **Reduced-motion aware** | `prefers-reduced-motion` switches the animation to the included static PNG. |
| 🎯 | **Strictly visual scope** | Decorates only the Web turn-status surface; it has no settings, model tools, storage, workspace access, network calls, or user-content processing. |
| ♻️ | **Lifecycle-clean** | The package-owned style belongs to the Cordis client fiber and is removed completely when the plugin stops or is uninstalled. |
| 🔌 | **Persistent DSH plugin** | The `dsh.bundle` manifest and `cordis.patch.yml` mount the client automatically in the Web profile. |

## Install

Install directly from GitHub into the DSH Web profile:

```powershell
dsh plugin --profile web add github:LeemanCheung/dsh-whale-animation
```

Then hard-refresh the DSH Web page. Restart DSH if the running profile has already cached its client bundle.

For the current release, pin `#v0.3.0`:

```powershell
dsh plugin --profile web add github:LeemanCheung/dsh-whale-animation#v0.3.0
```

### Uninstall

```powershell
dsh plugin --profile web remove dsh-whale-animation
```

## Animation profile

| Property | Value |
|---|---:|
| Canvas | 352 × 352 px (displayed at 84 × 84 CSS px) |
| Source frames | 60 unique native drawings |
| Frame duration | 33 ms |
| Loop duration | 1.980 s |
| Encoding | Lossless animated WebP with alpha |
| Reduced-motion asset | Transparent PNG |
| Runtime asset requests | None |

The final encoded WebP is decoded during validation—not merely checked at the source-frame level. It contains 60 unique frames at 33 ms each; the current closed-loop seam has an alpha-difference score of `0.00306` and a centroid step of `0.27 px`. Body area never falls below 98.7% of the median, so entry and deep-dive frames keep the whale visible.

The water layer combines a closed travelling wave with two damped wave packets. The cycle contains 59 continuously changing surface profiles with an exact last-to-first closure; the maximum crest-to-trough span is `23.45 px`, while the maximum mean adjacent-profile change is `1.90 px`, making the motion visible without flicker.

## How it works

```mermaid
flowchart LR
  A[Animated WebP + static PNG] --> B[scripts/build-client.mjs]
  B --> C[Embedded data URLs]
  C --> D[DSH client bundle]
  D --> E[Turn-status ::after element]
  F[prefers-reduced-motion] --> D
```

The client adds a package-owned stylesheet to the DSH turn-status element. Both assets are embedded as data URLs in `lib/client.js`, so activation does not depend on the repository checkout after installation.

## Development

Requirements: **Node.js 20+**. Python and Pillow are needed only when rebuilding the README artwork.

```powershell
node scripts/build-client.mjs
node scripts/check.mjs
python scripts/build-readme-assets.py
python scripts/check-readme-assets.py
```

### Repository layout

```text
assets/
  whale-dive.webp        Full lossless animation
  whale-static.png       Reduced-motion fallback
docs/
  hero.png               README hero artwork
  preview.webp           Lightweight animated README preview
  screenshots/           Breach, apex, and deep-dive frame gallery
lib/
  client.js              Prebuilt DSH browser client
scripts/
  build-client.mjs       Embeds source assets into the client
  build-readme-assets.py Rebuilds repository artwork from the real animation
  check-readme-assets.py Validates artwork timing, size, and README links
  check.mjs              Validates registration, lifecycle, and embedded assets
cordis.patch.yml         Persistent DSH bundle composition patch
```

`lib/client.js` is committed intentionally: GitHub installs work without a package build or external asset fetch.

## Compatibility

- Targets the **DeepSeek Harness Web UI**.
- Requires a DSH version compatible with `@deepseek-ai/dsh-client-runtime ^0.1.0-rc.6`.
- Relies on the current turn-status CSS class pattern; a future DSH shell redesign may require a selector update.

## Attribution

This project is independent and is not affiliated with or endorsed by DeepSeek. The animation is an original UI illustration designed to harmonize with DeepSeek Harness' whale-themed status experience. See [NOTICE.md](NOTICE.md) for visual-design and trademark details.

## License

Released under the [MIT License](LICENSE).
