# NOCTURNE 1.1 — mobile release

## Online

https://rawcdn.githack.com/LeemanCheung/dsh-whale-animation/99048e7068e186976c6518bebb2af5994b8cd522/index.html

On the first visit, GitHack displays a repository confirmation screen. Select **Open the page**. No account is required. This is static CDN delivery of the immutable published commit, not a local or temporary development server. GitHack is a third-party free service without an uptime guarantee.

Published app commit: `99048e7068e186976c6518bebb2af5994b8cd522`.

## Mobile changes

- Separate sculpture, caption and controls; phone, landscape and tablet compositions.
- Dynamic viewport and safe-area support; observed stage resizing after orientation changes.
- Minimum 44 × 44 CSS-pixel phone targets. Horizontal drag rotates; vertical swipe scrolls; hold deconstructs and cancellation restores.
- Mobile poster preview with download and native sharing where available.
- Same-origin bundled Three.js r180, with a native WebGL fallback; phone frame-rate and rendering-resolution limits.

## Verification — 2026-09-05

**139 checks passed, 0 failed** across Chromium and WebKit. Viewports: 320×568, 360×740, 375×667, 390×844, 430×932, 844×390, 768×1024, and 1440×900. Checks cover visible Three.js output, composition and overflow, target sizes, chapters, touch, pause, focus, notes, export, safe areas, viewport changes and fallback. These are automated browser-engine tests on a hosted runner, not physical iPhone testing.

Mobile report: [TEST-REPORT-v1.1.json](TEST-REPORT-v1.1.json).

Mobile source publication run: https://github.com/LeemanCheung/dsh-whale-animation/actions/runs/33949639541 — all mobile/browser checks and source publication passed; its earlier non-browser HTTP preflight failed with HTTP 403. The public browser check below supersedes that preflight, and future publication now uses browser navigation.

**Public browser verification passed:** https://github.com/LeemanCheung/dsh-whale-animation/actions/runs/33949944226

Both production and development CDN entries returned HTTP 200. A normal browser entered through the visible **Open the page** control, loaded **Three.js r180**, rendered the artwork, checked horizontal overflow and switched to the third sculpture. The production entry recorded no failed requests and no JavaScript errors. Online mobile screenshots and request evidence are available in the `nocturne-public-browser` workflow artifact.

## Repository isolation

All website files are on `nocturne-site`. The original plugin's `main` branch and releases were not changed. Main remained at `e1b746fd8048df6f5c896ac125c82498733f5be0` during publication.
