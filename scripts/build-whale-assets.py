#!/usr/bin/env python3
"""Generate six whale loops, reduced-motion frames, and README artwork."""

from __future__ import annotations

import json
import shutil

from whale_assets.model import ASSETS, DOCS, FRAME_MS, FRAMES
from whale_assets.states import state_specs
from whale_assets.visuals import build_gallery, build_hero, build_preview, save_animation, sha256


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    legacy_static = ASSETS / "whale-static.png"
    if legacy_static.exists():
        legacy_static.unlink()
    legacy_screenshots = DOCS / "screenshots"
    if legacy_screenshots.exists():
        shutil.rmtree(legacy_screenshots)
    specs = state_specs()
    frames_by_state = {}
    manifest_states = {}

    for spec in specs:
        frames = [spec.render(index / FRAMES) for index in range(FRAMES)]
        frames_by_state[spec.key] = frames
        animated_path = ASSETS / f"whale-{spec.key}.webp"
        static_path = ASSETS / f"whale-{spec.key}.png"
        save_animation(animated_path, frames)
        frames[spec.preview_frame].save(static_path, optimize=True)
        manifest_states[spec.key] = {
            "label": spec.label,
            "summary": spec.summary,
            "playlist": spec.playlist,
            "animated": animated_path.name,
            "static": static_path.name,
            "frames": FRAMES,
            "frameDurationMs": FRAME_MS,
            "loopDurationMs": FRAMES * FRAME_MS,
            "animatedBytes": animated_path.stat().st_size,
            "staticBytes": static_path.stat().st_size,
            "animatedSha256": sha256(animated_path),
            "staticSha256": sha256(static_path),
        }

    manifest = {
        "schemaVersion": 1,
        "canvas": [352, 352],
        "defaultState": "dive",
        "playlist": [spec.key for spec in specs if spec.playlist],
        "playlistIntervalMs": 9000,
        "states": manifest_states,
    }
    (ASSETS / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    build_hero(frames_by_state, specs)
    build_preview(frames_by_state, specs)
    build_gallery(frames_by_state, specs)

    print(json.dumps({
        "states": {key: {
            "animatedBytes": value["animatedBytes"],
            "staticBytes": value["staticBytes"],
        } for key, value in manifest_states.items()},
        "bundleAnimatedBytes": sum(int(value["animatedBytes"]) for value in manifest_states.values()),
        "bundleStaticBytes": sum(int(value["staticBytes"]) for value in manifest_states.values()),
        "heroBytes": (DOCS / "hero.png").stat().st_size,
        "previewBytes": (DOCS / "preview.webp").stat().st_size,
        "galleryBytes": (DOCS / "state-gallery.png").stat().st_size,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
