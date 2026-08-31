#!/usr/bin/env python3
"""Build and verify visible-frame continuity evidence for every whale state."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import statistics
from pathlib import Path

import PIL
from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageOps, ImageStat


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
DOCS = ROOT / "docs"
MANIFEST_PATH = ASSETS / "manifest.json"
REPORT_PATH = DOCS / "motion-audit.json"
CONTACT_SHEET_PATH = DOCS / "motion-contact-sheet.png"
VISIBLE_ALPHA = 32
MIN_VISIBLE_UNIQUE_RATIO = 0.5
MAX_STEP_RATIO = 2.5
MAX_LOOP_RATIO = 2.5
MAX_ZERO_STEP_RATIO = 0.1
MAX_ABSOLUTE_STEP = 0.04
MAX_FOREGROUND_STEP = 0.2
MAX_CENTROID_STEP_PX = 4.0
MAX_APPEARANCE_CENTROID_STEP_PX = 4.0
MAX_LEGACY_DERIVED_CENTROID_STEP_PX = 24.0
MAX_LEGACY_DERIVED_APPEARANCE_CENTROID_STEP_PX = 24.0
MIN_STEP_FOREGROUND_COVERAGE = 0.05
MIN_MEDIAN_FOREGROUND_COVERAGE = 0.1
SAMPLES_PER_STATE = 12
REQUIRED_PILLOW = "12.1.1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_frames(path: Path) -> list[Image.Image]:
    image = Image.open(path)
    frames: list[Image.Image] = []
    for index in range(int(getattr(image, "n_frames", 1))):
        image.seek(index)
        frames.append(image.convert("RGBA").copy())
    return frames


def normalize_visible(frame: Image.Image) -> Image.Image:
    pixels = bytearray(frame.tobytes())
    for offset in range(0, len(pixels), 4):
        alpha = pixels[offset + 3]
        if alpha < VISIBLE_ALPHA:
            pixels[offset:offset + 4] = b"\0\0\0\0"
        else:
            pixels[offset] = round(pixels[offset] * alpha / 255)
            pixels[offset + 1] = round(pixels[offset + 1] * alpha / 255)
            pixels[offset + 2] = round(pixels[offset + 2] * alpha / 255)
    return Image.frombytes("RGBA", frame.size, bytes(pixels))


def difference_score(left: Image.Image, right: Image.Image) -> float:
    require(left.size == right.size, "Motion comparison requires one native canvas per state")
    means = ImageStat.Stat(ImageChops.difference(left, right)).mean
    return sum(means) / len(means) / 255


def foreground_difference_score(left: Image.Image, right: Image.Image) -> float:
    require(left.size == right.size, "Foreground comparison requires one native canvas per state")
    alpha = ImageChops.lighter(left.getchannel("A"), right.getchannel("A"))
    mask = alpha.point(lambda value: 255 if value >= VISIBLE_ALPHA else 0)
    require(mask.getbbox() is not None, "Motion comparison has no visible foreground")
    means = ImageStat.Stat(ImageChops.difference(left, right), mask=mask).mean
    return sum(means) / len(means) / 255


def changed_foreground_coverage(left: Image.Image, right: Image.Image) -> float:
    require(left.size == right.size, "Coverage comparison requires one native canvas per state")
    alpha = ImageChops.lighter(left.getchannel("A"), right.getchannel("A"))
    visible = alpha.point(lambda value: 255 if value >= VISIBLE_ALPHA else 0)
    visible_pixels = visible.histogram()[255]
    require(visible_pixels > 0, "Coverage comparison has no visible foreground")
    difference = ImageChops.difference(left, right)
    maximum = ImageChops.lighter(
        ImageChops.lighter(difference.getchannel("R"), difference.getchannel("G")),
        ImageChops.lighter(difference.getchannel("B"), difference.getchannel("A")),
    )
    changed = maximum.point(lambda value: 255 if value >= 4 else 0)
    changed_visible = ImageChops.multiply(changed, visible)
    return changed_visible.histogram()[255] / visible_pixels


def visible_centroid(frame: Image.Image) -> tuple[float, float]:
    alpha = frame.getchannel("A").tobytes()
    width, height = frame.size
    total = 0
    weighted_x = 0
    weighted_y = 0
    for y in range(height):
        row = alpha[y * width:(y + 1) * width]
        row_total = sum(row)
        total += row_total
        weighted_y += y * row_total
        weighted_x += sum(x * value for x, value in enumerate(row))
    require(total > 0, "Centroid comparison has no visible foreground")
    return weighted_x / total, weighted_y / total


def appearance_centroid(frame: Image.Image) -> tuple[float, float]:
    pixels = frame.tobytes()
    width, height = frame.size
    total = 0
    weighted_x = 0
    weighted_y = 0
    stride = width * 4
    for y in range(height):
        row = pixels[y * stride:(y + 1) * stride]
        row_total = 0
        row_x = 0
        for x in range(width):
            offset = x * 4
            weight = row[offset] + row[offset + 1] + row[offset + 2] + row[offset + 3]
            row_total += weight
            row_x += x * weight
        total += row_total
        weighted_y += y * row_total
        weighted_x += row_x
    require(total > 0, "Appearance centroid has no visible content")
    return weighted_x / total, weighted_y / total


def centroid_distance(left: tuple[float, float], right: tuple[float, float]) -> float:
    return ((left[0] - right[0]) ** 2 + (left[1] - right[1]) ** 2) ** 0.5


def analyze_state(state: str, spec: dict[str, object]) -> tuple[dict[str, object], list[Image.Image]]:
    frames = load_frames(ASSETS / str(spec["animated"]))
    require(frames, f"{state}: animation has no frames")
    require(len(frames) == int(spec["frames"]), f"{state}: frame count differs from manifest")
    require(all(frame.getbbox() is not None for frame in frames), f"{state}: animation contains a blank frame")

    visible_frames = [normalize_visible(frame) for frame in frames]
    centroids = [visible_centroid(frame) for frame in visible_frames]
    appearance_centroids = [appearance_centroid(frame) for frame in visible_frames]
    visible_unique = len({sha256(frame.tobytes()) for frame in visible_frames})
    ordinary_steps = [difference_score(left, right) for left, right in zip(visible_frames, visible_frames[1:])]
    foreground_steps = [foreground_difference_score(left, right) for left, right in zip(visible_frames, visible_frames[1:])]
    foreground_coverages = [changed_foreground_coverage(left, right) for left, right in zip(visible_frames, visible_frames[1:])]
    nonzero_steps = [value for value in ordinary_steps if value > 0]
    require(nonzero_steps, f"{state}: animation has no visible motion")
    median_step = statistics.median(nonzero_steps)
    max_step = max(ordinary_steps)
    loop_step = difference_score(visible_frames[-1], visible_frames[0])
    max_foreground_step = max(foreground_steps)
    loop_foreground_step = foreground_difference_score(visible_frames[-1], visible_frames[0])
    loop_foreground_coverage = changed_foreground_coverage(visible_frames[-1], visible_frames[0])
    median_foreground_coverage = statistics.median(foreground_coverages)
    centroid_steps = [centroid_distance(left, right) for left, right in zip(centroids, centroids[1:])]
    loop_centroid_step = centroid_distance(centroids[-1], centroids[0])
    appearance_centroid_steps = [
        centroid_distance(left, right)
        for left, right in zip(appearance_centroids, appearance_centroids[1:])
    ]
    loop_appearance_centroid_step = centroid_distance(appearance_centroids[-1], appearance_centroids[0])
    zero_step_ratio = sum(value == 0 for value in ordinary_steps) / len(ordinary_steps)
    max_ratio = max_step / median_step
    loop_ratio = loop_step / median_step

    source = str(spec.get("source", "unknown"))
    if source == "generated":
        legacy_derived = bool(spec.get("derivedFrom"))
        centroid_limit = MAX_LEGACY_DERIVED_CENTROID_STEP_PX if legacy_derived else MAX_CENTROID_STEP_PX
        appearance_centroid_limit = (
            MAX_LEGACY_DERIVED_APPEARANCE_CENTROID_STEP_PX
            if legacy_derived
            else MAX_APPEARANCE_CENTROID_STEP_PX
        )
        minimum_unique = max(2, round(len(frames) * MIN_VISIBLE_UNIQUE_RATIO))
        require(
            visible_unique >= minimum_unique,
            f"{state}: only {visible_unique}/{len(frames)} visibly distinct frames; "
            "hidden alpha pixels do not count",
        )
        require(max_ratio <= MAX_STEP_RATIO, f"{state}: abrupt internal transition ratio {max_ratio:.3f}")
        require(loop_ratio <= MAX_LOOP_RATIO, f"{state}: abrupt loop seam ratio {loop_ratio:.3f}")
        require(zero_step_ratio <= MAX_ZERO_STEP_RATIO, f"{state}: too many frozen adjacent frames {zero_step_ratio:.3f}")
        require(max_step <= MAX_ABSOLUTE_STEP, f"{state}: absolute full-canvas step {max_step:.3f} is too large")
        require(loop_step <= MAX_ABSOLUTE_STEP, f"{state}: absolute full-canvas loop seam {loop_step:.3f} is too large")
        require(max_foreground_step <= MAX_FOREGROUND_STEP, f"{state}: foreground step {max_foreground_step:.3f} is too large")
        require(loop_foreground_step <= MAX_FOREGROUND_STEP, f"{state}: foreground loop seam {loop_foreground_step:.3f} is too large")
        require(min(foreground_coverages) >= MIN_STEP_FOREGROUND_COVERAGE, f"{state}: adjacent frames move too little visible foreground")
        require(median_foreground_coverage >= MIN_MEDIAN_FOREGROUND_COVERAGE, f"{state}: median visible foreground motion is too small")
        require(loop_foreground_coverage >= MIN_STEP_FOREGROUND_COVERAGE, f"{state}: loop seam has too little visible foreground motion")
        require(max(centroid_steps) <= centroid_limit, f"{state}: visible centroid teleports {max(centroid_steps):.3f}px")
        require(loop_centroid_step <= centroid_limit, f"{state}: loop centroid teleports {loop_centroid_step:.3f}px")
        require(max(appearance_centroid_steps) <= appearance_centroid_limit, f"{state}: visible appearance teleports {max(appearance_centroid_steps):.3f}px")
        require(loop_appearance_centroid_step <= appearance_centroid_limit, f"{state}: loop appearance teleports {loop_appearance_centroid_step:.3f}px")

    sample_indices = [round(index * (len(frames) - 1) / (SAMPLES_PER_STATE - 1)) for index in range(SAMPLES_PER_STATE)]

    result = {
        "source": source,
        "derivedFrom": spec.get("derivedFrom", []),
        "canvas": list(frames[0].size),
        "frames": len(frames),
        "visibleUniqueFrames": visible_unique,
        "visibleMotionSha256": sha256(b"".join(frame.tobytes() for frame in visible_frames)),
        "sampleIndices": sample_indices,
        "sampleVisibleSha256": [sha256(visible_frames[index].tobytes()) for index in sample_indices],
        "zeroStepRatio": round(zero_step_ratio, 3),
        "medianStep": round(median_step, 6),
        "maxStep": round(max_step, 6),
        "maxStepRatio": round(max_ratio, 3),
        "loopStep": round(loop_step, 6),
        "loopSeamRatio": round(loop_ratio, 3),
        "maxForegroundStep": round(max_foreground_step, 6),
        "loopForegroundStep": round(loop_foreground_step, 6),
        "minimumForegroundCoverage": round(min(foreground_coverages), 3),
        "medianForegroundCoverage": round(median_foreground_coverage, 3),
        "loopForegroundCoverage": round(loop_foreground_coverage, 3),
        "medianCentroidStepPx": round(statistics.median(centroid_steps), 3),
        "maxCentroidStepPx": round(max(centroid_steps), 3),
        "loopCentroidStepPx": round(loop_centroid_step, 3),
        "medianAppearanceCentroidStepPx": round(statistics.median(appearance_centroid_steps), 3),
        "maxAppearanceCentroidStepPx": round(max(appearance_centroid_steps), 3),
        "loopAppearanceCentroidStepPx": round(loop_appearance_centroid_step, 3),
    }
    return result, frames


def font(size: int) -> ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def render_contact_sheet(
    state_order: list[str],
    analyses: dict[str, dict[str, object]],
    frames_by_state: dict[str, list[Image.Image]],
) -> bytes:
    label_width = 190
    cell_width = 92
    cell_height = 104
    margin = 20
    header_height = 58
    width = margin * 2 + label_width + SAMPLES_PER_STATE * cell_width
    height = header_height + margin + len(state_order) * cell_height + margin
    sheet = Image.new("RGBA", (width, height), (239, 246, 255, 255))
    draw = ImageDraw.Draw(sheet, "RGBA")
    draw.text((margin, 16), "Whale motion continuity · 12 samples per state", font=font(22), fill=(8, 24, 46, 255))

    for row, state in enumerate(state_order):
        top = header_height + margin + row * cell_height
        analysis = analyses[state]
        draw.rounded_rectangle(
            (margin, top, width - margin, top + cell_height - 8),
            radius=14,
            fill=(255, 255, 255, 244),
            outline=(190, 211, 239, 255),
            width=1,
        )
        draw.text((margin + 14, top + 15), state.upper(), font=font(15), fill=(8, 24, 46, 255))
        metrics = f"unique {analysis['visibleUniqueFrames']}/{analysis['frames']}  seam {analysis['loopSeamRatio']:.2f}x"
        draw.text((margin + 14, top + 43), metrics, font=font(10), fill=(58, 83, 119, 255))

        frames = frames_by_state[state]
        sample_indices = analysis["sampleIndices"]
        for column, frame_index in enumerate(sample_indices):
            thumb = ImageOps.contain(frames[frame_index], (76, 76), Image.Resampling.LANCZOS)
            x = margin + label_width + column * cell_width + (cell_width - thumb.width) // 2
            y = top + 8 + (80 - thumb.height) // 2
            sheet.alpha_composite(thumb, (x, y))
            draw.text(
                (margin + label_width + column * cell_width + 5, top + 78),
                f"{frame_index + 1:03d}",
                font=font(9),
                fill=(80, 101, 132, 255),
            )

    output = io.BytesIO()
    sheet.convert("RGB").save(output, format="PNG", optimize=False)
    return output.getvalue()


def build_evidence() -> tuple[dict[str, object], bytes]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    canonical_manifest = json.dumps(
        manifest,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    state_order = list(manifest["states"])
    analyses: dict[str, dict[str, object]] = {}
    frames_by_state: dict[str, list[Image.Image]] = {}
    for state in state_order:
        analyses[state], frames_by_state[state] = analyze_state(state, manifest["states"][state])
    generated_motion = [
        analyses[state]["visibleMotionSha256"]
        for state in state_order
        if analyses[state]["source"] == "generated"
    ]
    require(len(set(generated_motion)) == len(generated_motion), "Generated semantic states share the same visible animation")

    contact_sheet = render_contact_sheet(state_order, analyses, frames_by_state)
    with Image.open(io.BytesIO(contact_sheet)) as sheet:
        sheet_size = list(sheet.size)
    report = {
        "schemaVersion": 1,
        "assetManifestSha256": sha256(canonical_manifest),
        "stateOrder": state_order,
        "thresholds": {
            "visibleAlpha": VISIBLE_ALPHA,
            "minimumVisibleUniqueRatio": MIN_VISIBLE_UNIQUE_RATIO,
            "maximumStepRatio": MAX_STEP_RATIO,
            "maximumLoopSeamRatio": MAX_LOOP_RATIO,
            "maximumZeroStepRatio": MAX_ZERO_STEP_RATIO,
            "maximumAbsoluteStep": MAX_ABSOLUTE_STEP,
            "maximumForegroundStep": MAX_FOREGROUND_STEP,
            "maximumCentroidStepPx": MAX_CENTROID_STEP_PX,
            "maximumAppearanceCentroidStepPx": MAX_APPEARANCE_CENTROID_STEP_PX,
            "maximumLegacyDerivedCentroidStepPx": MAX_LEGACY_DERIVED_CENTROID_STEP_PX,
            "maximumLegacyDerivedAppearanceCentroidStepPx": MAX_LEGACY_DERIVED_APPEARANCE_CENTROID_STEP_PX,
            "minimumStepForegroundCoverage": MIN_STEP_FOREGROUND_COVERAGE,
            "minimumMedianForegroundCoverage": MIN_MEDIAN_FOREGROUND_COVERAGE,
        },
        "states": analyses,
        "contactSheet": {
            "file": "motion-contact-sheet.png",
            "size": sheet_size,
            "sha256": sha256(contact_sheet),
        },
    }
    return report, contact_sheet


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="write deterministic evidence files")
    mode.add_argument("--check", action="store_true", help="verify committed evidence files")
    args = parser.parse_args()
    require(
        PIL.__version__ == REQUIRED_PILLOW,
        f"Pillow {REQUIRED_PILLOW} is required; found {PIL.__version__}. "
        "Install requirements.txt before building or auditing assets.",
    )

    report, contact_sheet = build_evidence()
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        DOCS.mkdir(parents=True, exist_ok=True)
        CONTACT_SHEET_PATH.write_bytes(contact_sheet)
        REPORT_PATH.write_text(serialized, encoding="utf-8")
    else:
        require(REPORT_PATH.is_file(), "Motion audit report is missing; run --write")
        require(CONTACT_SHEET_PATH.is_file(), "Motion contact sheet is missing; run --write")
        stored_report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        expected_report = dict(report)
        expected_report["contactSheet"] = stored_report.get("contactSheet")
        require(stored_report == expected_report, "Motion audit report is stale")
        stored_sheet = CONTACT_SHEET_PATH.read_bytes()
        with Image.open(io.BytesIO(stored_sheet)) as image:
            stored_image = image.convert("RGB")
            stored_size = list(stored_image.size)
        with Image.open(io.BytesIO(contact_sheet)) as image:
            expected_image = image.convert("RGB")
        require(stored_size == stored_report["contactSheet"]["size"], "Motion contact sheet dimensions changed")
        require(sha256(stored_sheet) == stored_report["contactSheet"]["sha256"], "Motion contact sheet hash changed")
        require(ImageChops.difference(stored_image, expected_image).getbbox() is None, "Motion contact sheet is not rendered from current sampled frames")
        report["contactSheet"] = stored_report["contactSheet"]

    print(json.dumps({
        "ok": True,
        "mode": "write" if args.write else "check",
        "states": report["states"],
        "contactSheet": report["contactSheet"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
