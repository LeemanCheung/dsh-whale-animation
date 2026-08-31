#!/usr/bin/env python3
"""Build brand-aligned whale states while preserving two legacy loops byte-for-byte."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import PIL
from PIL import Image

from whale_assets.model import ASSETS, CANVAS, DOCS, FRAME_MS, FRAMES
from whale_assets.states import state_specs
from whale_assets.visuals import (
    build_gallery,
    build_hero,
    build_preview,
    build_rebuilt_real_speed_preview,
    save_animation,
    sha256,
)


PLAYLIST_INTERVAL_MS = 11_000
REQUIRED_PILLOW = "12.1.1"
SPOUT_REPORT = Path(__file__).resolve().parents[1] / "artwork-sources" / "spout-imagegen-v1" / "build-report.json"


def load_animation(path: Path) -> tuple[list[Image.Image], list[int]]:
    image = Image.open(path)
    frames: list[Image.Image] = []
    durations: list[int] = []
    frame_count = int(getattr(image, "n_frames", 1))
    for index in range(frame_count):
        image.seek(index)
        frames.append(image.convert("RGBA").copy())
        durations.append(int(image.info.get("duration", 0) or FRAME_MS))
    return frames, durations


def uniform_duration(durations: list[int], state: str) -> int:
    values = set(durations)
    if len(values) != 1:
        raise RuntimeError(f"{state}: legacy loop must use a uniform cadence, got {sorted(values)}")
    return durations[0]


def profile_entry(
    *,
    spec,
    animated_path: Path,
    static_path: Path,
    frames: list[Image.Image],
    durations: list[int],
) -> dict[str, object]:
    frame_duration = uniform_duration(durations, spec.key)
    entry: dict[str, object] = {
        "label": spec.label,
        "summary": spec.summary,
        "playlist": spec.playlist,
        "source": spec.source,
        "animated": animated_path.name,
        "static": static_path.name,
        "canvas": list(frames[0].size),
        "frames": len(frames),
        "frameDurationMs": frame_duration,
        "loopDurationMs": sum(durations),
        "animatedBytes": animated_path.stat().st_size,
        "staticBytes": static_path.stat().st_size,
        "animatedSha256": sha256(animated_path),
        "staticSha256": sha256(static_path),
    }
    if spec.preserved_from:
        entry["preservedFrom"] = spec.preserved_from
    if spec.derived_from:
        entry["derivedFrom"] = list(spec.derived_from)
    return entry


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-docs",
        action="store_true",
        help="rebuild runtime assets and manifest without system-font-dependent docs",
    )
    args = parser.parse_args()
    if PIL.__version__ != REQUIRED_PILLOW:
        raise RuntimeError(
            f"Pillow {REQUIRED_PILLOW} is required; found {PIL.__version__}. "
            "Install requirements.txt before rebuilding assets."
        )
    ASSETS.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    specs = state_specs()
    frames_by_state: dict[str, list[Image.Image]] = {}
    manifest_states: dict[str, dict[str, object]] = {}

    for spec in specs:
        animated_path = ASSETS / f"whale-{spec.key}.webp"
        static_path = ASSETS / f"whale-{spec.key}.png"
        if spec.source in {"legacy", "imagegen"}:
            if not animated_path.is_file() or not static_path.is_file():
                raise RuntimeError(
                    f"Missing prebuilt assets for {spec.key}: "
                    f"{animated_path.name}, {static_path.name}"
                )
            frames, durations = load_animation(animated_path)
        else:
            if spec.render is None:
                raise RuntimeError(f"Generated state {spec.key} does not have a renderer")
            frames = [spec.render(index / FRAMES) for index in range(FRAMES)]
            durations = [FRAME_MS] * FRAMES
            save_animation(animated_path, frames)
            frames[spec.preview_frame % len(frames)].save(static_path, optimize=True)
        if not frames:
            raise RuntimeError(f"{spec.key}: animation has no frames")
        native_canvas = frames[0].size
        if any(frame.size != native_canvas for frame in frames):
            raise RuntimeError(f"{spec.key}: animation frames do not share one native canvas")
        if spec.source != "legacy" and native_canvas != (CANVAS, CANVAS):
            raise RuntimeError(f"{spec.key}: generated state must use {CANVAS}x{CANVAS} frames")
        static_image = Image.open(static_path)
        if static_image.size != native_canvas:
            raise RuntimeError(
                f"{spec.key}: reduced-motion image {static_image.size} does not match "
                f"the native animation canvas {native_canvas}"
            )
        frames_by_state[spec.key] = frames
        manifest_states[spec.key] = profile_entry(
            spec=spec,
            animated_path=animated_path,
            static_path=static_path,
            frames=frames,
            durations=durations,
        )
        if spec.key == "spout":
            report = json.loads(SPOUT_REPORT.read_text(encoding="utf-8"))
            manifest_states[spec.key].update({
                "provenanceReport": "artwork-sources/spout-imagegen-v1/build-report.json",
                "sourceSheets": [
                    f"artwork-sources/spout-imagegen-v1/{name}"
                    for name in report["inputs"]["phaseSheets"]
                ],
                "nativeImageGenCels": report["inputs"]["nativeImageGenCels"],
                "spoutSegmentFrames": report["output"]["spoutFramesSecond"],
                "cycleSegments": report["output"]["segments"],
            })

    manifest = {
        "schemaVersion": 1,
        "canvas": [CANVAS, CANVAS],
        "canvasScope": "generated-states",
        "defaultState": "dive",
        "playlist": [spec.key for spec in specs if spec.playlist],
        "playlistIntervalMs": PLAYLIST_INTERVAL_MS,
        "states": manifest_states,
    }
    (ASSETS / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not args.skip_docs:
        build_hero(frames_by_state, specs)
        build_preview(frames_by_state, specs)
        build_rebuilt_real_speed_preview(frames_by_state)
        build_gallery(frames_by_state, specs)
        real_speed_path = DOCS / "rebuilt-states-real-speed.webp"
        real_speed_report = {
            "schemaVersion": 1,
            "file": real_speed_path.name,
            "sha256": sha256(real_speed_path),
            "size": [1000, 300],
            "frames": FRAMES,
            "frameDurationMs": FRAME_MS,
            "loopDurationMs": FRAMES * FRAME_MS,
            "states": {
                state: manifest_states[state]["animatedSha256"]
                for state in ("work", "compose", "idle", "alert")
            },
        }
        (DOCS / "rebuilt-states-real-speed.json").write_text(
            json.dumps(real_speed_report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    result = {
        "states": {
            key: {
                "source": value["source"],
                "canvas": value["canvas"],
                "frames": value["frames"],
                "frameDurationMs": value["frameDurationMs"],
                "animatedBytes": value["animatedBytes"],
                "staticBytes": value["staticBytes"],
            }
            for key, value in manifest_states.items()
        },
        "bundleAnimatedBytes": sum(int(value["animatedBytes"]) for value in manifest_states.values()),
        "bundleStaticBytes": sum(int(value["staticBytes"]) for value in manifest_states.values()),
        "docsRebuilt": not args.skip_docs,
    }
    if not args.skip_docs:
        result.update({
            "heroBytes": (DOCS / "hero.png").stat().st_size,
            "previewBytes": (DOCS / "preview.webp").stat().st_size,
            "realSpeedPreviewBytes": (DOCS / "rebuilt-states-real-speed.webp").stat().st_size,
            "galleryBytes": (DOCS / "state-gallery.png").stat().st_size,
        })
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
