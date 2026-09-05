# DSH 0.1.2-rc.1 compatibility and playback

Checked 2026-09-05 for dsh-whale-animation 0.7.1.

The exact release matrix and successful Host/Client activation in the real QA 3081 and original Web 3080 Profiles are recorded in [COMPATIBILITY.md](../COMPATIBILITY.md). Unverified older alpha releases remain unknown.

- The new DSH client no longer provides `dsh-client-runtime`. This plugin has no imports from that package, so its obsolete browser injection and peer were removed. Cordis 4.0.2 supplies the effect lifecycle.
- The installed `dsh-client-ui-chat@0.1.2-rc.1` still renders the turn status with a `turnStatus` CSS-module class, `role="status"`, and `aria-live="polite"`.
- Both original raster assets retain their exact Git blobs, SHA-256 values, dimensions, frame counts and timing. No SVG or additional action state was added.
- Dive completes its 1,980 ms loop before Classic begins its 10,506 ms loop. A text-driven action change also waits for the active loop. Delayed same-state callbacks retain the existing decoder clock. Hiding the page releases its image; returning restarts that same action from its first frame.
- A fresh disposable Blob URL avoids sharing another element's animation position. Every created URL is revoked on replacement, disconnection or disposal. Operating-system dark mode no longer overrides an explicit light app theme.
- Generated JavaScript uses LF regardless of source checkout line endings; CI verifies committed outputs on Windows and Linux.

## Verification

`npm run verify` passes asset identity checks, package injection checks, state-selection boundaries, deferred changes, hidden/resume behavior, timer drift and Blob cleanup. The final independent read-only review passed the two timer regression cases.

`python scripts/check-playback.py` uses Python Playwright and installed Chrome against the actual built client. The last real-time run measured 1,983.7 ms and 10,507.2 ms between state changes, with an allowed 150 ms scheduling tolerance. It also passed desktop, 390 px, dark theme, light app theme on a dark OS, reduced-motion PNG, zero-SVG, zero-page-error and disposal checks. This measures real browser action timing; it is not a claim that every display presents every encoded frame.

The local report and screenshots are generated under `.artifacts/playback-*`. This test does not connect to a provider or modify a DSH profile.
