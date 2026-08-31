#!/usr/bin/env python3
"""Validate black-ink identity and render true-size 60/84 px visual evidence."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from collections import deque
from pathlib import Path

import PIL
from PIL import Image, ImageChops, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
DOCS = ROOT / "docs"
REPORT_PATH = DOCS / "style-identity-audit.json"
CONTACT_SHEET_PATH = DOCS / "style-identity-contact-sheet.png"
REQUIRED_PILLOW = "12.1.1"
VISIBLE_ALPHA = 32
TARGET_STATES = ("work", "compose", "idle", "alert")
DISPLAY_STATES = ("dive", "classic", *TARGET_STATES)
DISPLAY_FRAMES = {
    "dive": 22,
    "classic": 112,
    "work": 18,
    "compose": 12,
    "idle": 12,
    "alert": 24,
}
DISPLAY_SIZES = (84, 60)
MAX_CHROMATIC_RATIO = 0.0
MAX_BLUE_DOMINANT_RATIO = 0.0
MAX_LIGHT_DETAIL_RATIO = 0.012
MIN_TRANSPARENT_RATIO = 0.45
MIN_MAIN_COMPONENT_RATIO = 0.52
MAX_MAIN_COMPONENT_HOLES = 4
MIN_MAIN_COMPONENT_WIDTH = {"84": 20, "60": 14}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_frame(path: Path, index: int) -> Image.Image:
    image = Image.open(path)
    frame_count = int(getattr(image, "n_frames", 1))
    image.seek(index % frame_count)
    return image.convert("RGBA").copy()


def load_all_frames(path: Path) -> list[Image.Image]:
    image = Image.open(path)
    frames: list[Image.Image] = []
    for index in range(int(getattr(image, "n_frames", 1))):
        image.seek(index)
        frames.append(image.convert("RGBA").copy())
    return frames


def palette_profile(frames: list[Image.Image]) -> dict[str, object]:
    visible = 0
    chromatic = 0
    blue_dominant = 0
    light_detail = 0
    transparent = 0
    total = 0
    alpha_extrema: set[tuple[int, int]] = set()
    for frame in frames:
        alpha_extrema.add(frame.getchannel("A").getextrema())
        for red, green, blue, alpha in frame.get_flattened_data():
            total += 1
            if alpha == 0:
                transparent += 1
            if alpha < VISIBLE_ALPHA:
                continue
            visible += 1
            if max(red, green, blue) - min(red, green, blue) > 4:
                chromatic += 1
            if blue > red + 2 and blue > green + 2:
                blue_dominant += 1
            if alpha > 200 and (red + green + blue) / 3 > 180:
                light_detail += 1
    require(visible > 0 and total > 0, "Style audit found no visible pixels")
    return {
        "alphaExtrema": [list(item) for item in sorted(alpha_extrema)],
        "transparentRatio": transparent / total,
        "chromaticVisibleRatio": chromatic / visible,
        "blueDominantVisibleRatio": blue_dominant / visible,
        "lightDetailVisibleRatio": light_detail / visible,
    }


def binary_mask(frame: Image.Image, size: int) -> tuple[list[list[bool]], int]:
    alpha = frame.getchannel("A").resize((size, size), Image.Resampling.LANCZOS)
    values = list(alpha.get_flattened_data())
    mask = [[False] * size for _ in range(size)]
    visible = 0
    for y in range(size):
        for x in range(size):
            active = values[y * size + x] >= VISIBLE_ALPHA
            mask[y][x] = active
            visible += int(active)
    return mask, visible


def connected_components(mask: list[list[bool]]) -> list[list[tuple[int, int]]]:
    height = len(mask)
    width = len(mask[0])
    visited = [[False] * width for _ in range(height)]
    components: list[list[tuple[int, int]]] = []
    for y in range(height):
        for x in range(width):
            if visited[y][x] or not mask[y][x]:
                continue
            queue = deque([(x, y)])
            visited[y][x] = True
            component: list[tuple[int, int]] = []
            while queue:
                px, py = queue.popleft()
                component.append((px, py))
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if 0 <= nx < width and 0 <= ny < height and mask[ny][nx] and not visited[ny][nx]:
                        visited[ny][nx] = True
                        queue.append((nx, ny))
            components.append(component)
    return components


def hole_count(component: list[tuple[int, int]]) -> int:
    min_x = min(point[0] for point in component)
    max_x = max(point[0] for point in component)
    min_y = min(point[1] for point in component)
    max_y = max(point[1] for point in component)
    width = max_x - min_x + 3
    height = max_y - min_y + 3
    filled = [[False] * width for _ in range(height)]
    for x, y in component:
        filled[y - min_y + 1][x - min_x + 1] = True
    visited = [[False] * width for _ in range(height)]
    queue = deque([(0, 0)])
    visited[0][0] = True
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height and not filled[ny][nx] and not visited[ny][nx]:
                visited[ny][nx] = True
                queue.append((nx, ny))
    holes = 0
    for y in range(height):
        for x in range(width):
            if filled[y][x] or visited[y][x]:
                continue
            holes += 1
            queue = deque([(x, y)])
            visited[y][x] = True
            while queue:
                px, py = queue.popleft()
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if 0 <= nx < width and 0 <= ny < height and not filled[ny][nx] and not visited[ny][nx]:
                        visited[ny][nx] = True
                        queue.append((nx, ny))
    return holes


def component_profile(frame: Image.Image, size: int) -> dict[str, object]:
    mask, visible = binary_mask(frame, size)
    components = connected_components(mask)
    require(components and visible > 0, f"{size}px identity sample has no visible silhouette")
    main = max(components, key=len)
    min_x = min(point[0] for point in main)
    max_x = max(point[0] for point in main)
    min_y = min(point[1] for point in main)
    max_y = max(point[1] for point in main)
    return {
        "visiblePixels": visible,
        "componentCount": len(components),
        "mainComponentPixels": len(main),
        "mainComponentRatio": len(main) / visible,
        "mainComponentBounds": [min_x, min_y, max_x + 1, max_y + 1],
        "mainComponentWidth": max_x - min_x + 1,
        "mainComponentHeight": max_y - min_y + 1,
        "mainComponentHoles": hole_count(main),
    }


def font(size: int) -> ImageFont.ImageFont:
    return ImageFont.load_default(size=size)


def render_contact_sheet(frames: dict[str, Image.Image]) -> bytes:
    column_width = 146
    left = 118
    header = 80
    row_height = 142
    width = left + column_width * len(DISPLAY_STATES) + 24
    height = header + row_height * len(DISPLAY_SIZES) + 28
    sheet = Image.new("RGBA", (width, height), (246, 248, 251, 255))
    draw = ImageDraw.Draw(sheet, "RGBA")
    draw.text((24, 18), "Dive / Classic identity gate · actual 84 px and 60 px runtime sizes", font=font(22), fill=(0, 0, 0, 255))
    draw.text((24, 48), "Targets must remain pure black ink with a simple, long-tail whale silhouette.", font=font(12), fill=(67, 76, 91, 255))
    for column, state in enumerate(DISPLAY_STATES):
        x = left + column * column_width
        role = "REFERENCE" if state in ("dive", "classic") else "TARGET"
        draw.text((x + 8, header - 2), state.upper(), font=font(14), fill=(0, 0, 0, 255))
        draw.text((x + 8, header + 19), role, font=font(9), fill=(76, 87, 104, 255))
    for row, size in enumerate(DISPLAY_SIZES):
        y = header + 38 + row * row_height
        draw.text((24, y + 14), f"{size} px", font=font(18), fill=(0, 0, 0, 255))
        draw.text((24, y + 41), "true size", font=font(10), fill=(76, 87, 104, 255))
        for column, state in enumerate(DISPLAY_STATES):
            x = left + column * column_width + (column_width - size) // 2
            tile = frames[state].resize((size, size), Image.Resampling.LANCZOS)
            draw.rectangle((x - 1, y - 1, x + size, y + size), fill=(255, 255, 255, 255), outline=(210, 215, 223, 255), width=1)
            sheet.alpha_composite(tile, (x, y))
    output = io.BytesIO()
    sheet.convert("RGB").save(output, format="PNG", optimize=False)
    return output.getvalue()


def build_evidence() -> tuple[dict[str, object], bytes]:
    manifest = json.loads((ASSETS / "manifest.json").read_text(encoding="utf-8"))
    display_frames = {
        state: load_frame(ASSETS / str(manifest["states"][state]["animated"]), DISPLAY_FRAMES[state])
        for state in DISPLAY_STATES
    }
    targets: dict[str, object] = {}
    for state in TARGET_STATES:
        entry = manifest["states"][state]
        frames = load_all_frames(ASSETS / str(entry["animated"]))
        static_frame = load_frame(ASSETS / str(entry["static"]), 0)
        require(
            ImageChops.difference(static_frame, display_frames[state]).getbbox() is None,
            f"{state}: reduced-motion PNG does not match animated frame {DISPLAY_FRAMES[state]}",
        )
        palette = palette_profile(frames)
        static_palette = palette_profile([static_frame])
        require(palette["alphaExtrema"] == [[0, 255]], f"{state}: animation is not true transparent RGBA")
        require(static_palette["alphaExtrema"] == [[0, 255]], f"{state}: reduced-motion PNG is not true transparent RGBA")
        require(palette["transparentRatio"] >= MIN_TRANSPARENT_RATIO, f"{state}: transparent canvas ratio is too small")
        require(static_palette["transparentRatio"] >= MIN_TRANSPARENT_RATIO, f"{state}: reduced-motion PNG transparent canvas ratio is too small")
        require(palette["chromaticVisibleRatio"] <= MAX_CHROMATIC_RATIO, f"{state}: colored pixels violate black-ink style")
        require(static_palette["chromaticVisibleRatio"] <= MAX_CHROMATIC_RATIO, f"{state}: reduced-motion PNG contains colored pixels")
        require(palette["blueDominantVisibleRatio"] <= MAX_BLUE_DOMINANT_RATIO, f"{state}: blue pixels are forbidden")
        require(static_palette["blueDominantVisibleRatio"] <= MAX_BLUE_DOMINANT_RATIO, f"{state}: reduced-motion PNG contains blue pixels")
        require(palette["lightDetailVisibleRatio"] <= MAX_LIGHT_DETAIL_RATIO, f"{state}: interior detail is too complex for the ink silhouette")
        require(static_palette["lightDetailVisibleRatio"] <= MAX_LIGHT_DETAIL_RATIO, f"{state}: reduced-motion PNG interior detail is too complex")
        sizes: dict[str, object] = {}
        for size in DISPLAY_SIZES:
            profile = component_profile(display_frames[state], size)
            require(profile["mainComponentRatio"] >= MIN_MAIN_COMPONENT_RATIO, f"{state}: {size}px pose fragments into effects")
            require(profile["mainComponentHoles"] <= MAX_MAIN_COMPONENT_HOLES, f"{state}: {size}px silhouette has complex internal holes")
            require(profile["mainComponentWidth"] >= MIN_MAIN_COMPONENT_WIDTH[str(size)], f"{state}: {size}px whale is too small to identify")
            sizes[str(size)] = profile
        targets[state] = {
            "framesChecked": len(frames),
            "staticMatchesAnimatedFrame": DISPLAY_FRAMES[state],
            "palette": {key: round(value, 6) if isinstance(value, float) else value for key, value in palette.items()},
            "staticPalette": {key: round(value, 6) if isinstance(value, float) else value for key, value in static_palette.items()},
            "display": {
                size: {key: round(value, 6) if isinstance(value, float) else value for key, value in profile.items()}
                for size, profile in sizes.items()
            },
        }
    contact_sheet = render_contact_sheet(display_frames)
    with Image.open(io.BytesIO(contact_sheet)) as image:
        sheet_size = list(image.size)
    return {
        "schemaVersion": 1,
        "identityAnchors": ["dive", "classic"],
        "targetStates": list(TARGET_STATES),
        "displayFrames": DISPLAY_FRAMES,
        "displaySizes": list(DISPLAY_SIZES),
        "thresholds": {
            "visibleAlpha": VISIBLE_ALPHA,
            "maximumChromaticVisibleRatio": MAX_CHROMATIC_RATIO,
            "maximumBlueDominantVisibleRatio": MAX_BLUE_DOMINANT_RATIO,
            "maximumLightDetailVisibleRatio": MAX_LIGHT_DETAIL_RATIO,
            "minimumTransparentRatio": MIN_TRANSPARENT_RATIO,
            "minimumMainComponentRatio": MIN_MAIN_COMPONENT_RATIO,
            "maximumMainComponentHoles": MAX_MAIN_COMPONENT_HOLES,
            "minimumMainComponentWidth": MIN_MAIN_COMPONENT_WIDTH,
        },
        "states": targets,
        "contactSheet": {
            "file": CONTACT_SHEET_PATH.name,
            "size": sheet_size,
            "sha256": sha256(contact_sheet),
        },
    }, contact_sheet


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    require(PIL.__version__ == REQUIRED_PILLOW, f"Pillow {REQUIRED_PILLOW} is required; found {PIL.__version__}")
    report, contact_sheet = build_evidence()
    serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        DOCS.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(serialized, encoding="utf-8")
        CONTACT_SHEET_PATH.write_bytes(contact_sheet)
    else:
        require(REPORT_PATH.is_file(), "Style identity report is missing; run --write")
        require(CONTACT_SHEET_PATH.is_file(), "Style identity contact sheet is missing; run --write")
        require(json.loads(REPORT_PATH.read_text(encoding="utf-8")) == report, "Style identity report is stale")
        stored_sheet = CONTACT_SHEET_PATH.read_bytes()
        require(sha256(stored_sheet) == report["contactSheet"]["sha256"], "Style identity contact sheet hash changed")
        with Image.open(io.BytesIO(stored_sheet)) as stored, Image.open(io.BytesIO(contact_sheet)) as expected:
            require(ImageChops.difference(stored.convert("RGB"), expected.convert("RGB")).getbbox() is None, "Style identity contact sheet is stale")
    print(json.dumps({"ok": True, "mode": "write" if args.write else "check", "states": report["states"], "contactSheet": report["contactSheet"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
