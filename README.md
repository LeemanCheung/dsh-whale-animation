# dsh-whale-animation

A quiet, monochrome whale beside DeepSeek Harness Web turn status. **v0.8.0 preserves Dive and Classic and adds four original ImageGen actions: Scout, Surge, Flow and Breathe.**

![Four new actions](docs/four-actions/preview.gif)

This20fps review GIF keeps each action's real timing. Runtime assets are native60fps WebPs.

| Action | Visual | Status wording |
| --- | --- | --- |
| Dive / Classic | Original bytes and timings retained | Original/default |
| Scout | Curious bubble tracking with a natural return trip | Searching / reading |
| Surge | Gentle torso flex and tail propulsion | Running / testing |
| Flow | A compact C-shaped body coils and relaxes | Writing / composing |
| Breathe | Arch, exhale and settle | Waiting / connecting |

Each new action uses8 generated drawings,32 in total, plus documented raster in-betweens. Scout is144 frames/2.4s, Surge120/2s, Flow180/3s and Breathe216/3.6s. Scout intentionally revisits poses on its return trip; playback frame count is not generated-art count.

## Behavior

- Original PNG/WebP bytes, frame counts and timing are hash-locked. They are never re-encoded.
- Unrecognized status text rotates all six actions. Status changes wait for a complete encoded cycle.
- Keyword matching chooses a visual, not a claim about actual tool success or completion.
- Preserve84/72/60px responsive sizes, light/dark themes, PNG reduced motion, hidden-tab suspension and complete disposal.
- Decode assets lazily and use static fallback if preparation fails.
- No SVG whales, external image requests, extra model calls, font overrides or user data/settings changes.

## Install

```powershell
dsh plugin --profile web add github:LeemanCheung/dsh-whale-animation
```

Load updates at a safe time for your existing sessions. Development verification uses an isolated DSH home and does not restart the user's daily service.

## Verify

```text
npm run verify
npm run check:package
npm run check:browser
```

For raster reconstruction from a full Git checkout:

```text
python -m pip install -r requirements-art.txt
npm run art:check
```

With Python Playwright and Chrome installed, run `npm run check:playback`. Read the [source and animation notes](docs/four-actions/README.md) and [exact compatibility record](COMPATIBILITY.md). Raw generation PNGs remain in Git; runtime packages include selected animation assets and lightweight provenance, not duplicate source sheets.

Independent project, not an official DeepSeek logo or animation. See [NOTICE](NOTICE.md).

English · [简体中文](README.zh-CN.md)
