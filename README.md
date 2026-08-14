# dsh-whale-animation

A persistent [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness) Web UI plugin that places a black whale-dive animation beside the turn status (such as **Deep diving...**).

The animation is a self-contained 184×184 lossless animated WebP with a reduced-motion PNG fallback. Its 618-frame closed trajectory eliminates the former end-to-start hard cut while keeping every frame at 17ms for 60Hz-safe playback.

## Install

Install from GitHub into the Web profile:

```powershell
dsh plugin --profile web add github:LeemanCheung/dsh-whale-animation
```

Then hard-refresh the DSH Web page. Restart DSH if the running profile has already cached its client bundle.

## Uninstall

```powershell
dsh plugin --profile web remove dsh-whale-animation
```

## What it changes

- Adds a pure-black whale animation immediately after the DSH turn-status label.
- Uses an embedded animated WebP; no network request or external asset path is required while DSH runs.
- Respects `prefers-reduced-motion` by using the included static PNG.
- Uses a closed forward/return trajectory so the loop does not snap from the final dive pose back to its first pose.

## Development

Requirements: Node.js 20 or newer.

```powershell
node scripts/build-client.mjs
node scripts/check.mjs
```

`assets/whale-dive.webp` and `assets/whale-static.png` are the source assets. `scripts/build-client.mjs` embeds them into `lib/client.js`, which is committed so GitHub installs work without a build step.

## Notes

This plugin targets the DSH Web UI only. It relies on the existing turn-status CSS class pattern, so a future DSH shell redesign may require a selector update.

This project is independent and is not affiliated with or endorsed by DeepSeek. See [NOTICE.md](NOTICE.md) for visual-design attribution details.

## License

MIT. See [LICENSE](LICENSE).
