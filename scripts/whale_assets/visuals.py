from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFilter

from .model import (
    DOCS,
    FONT_BOLD_CANDIDATES,
    FONT_MEDIUM_CANDIDATES,
    FONT_REGULAR_CANDIDATES,
    FRAME_MS,
    FRAMES,
    INK,
    StateSpec,
    WHITE,
    font,
    lerp,
)


def save_animation(path: Path, frames: Sequence[Image.Image], duration: int = FRAME_MS) -> None:
    frames[0].save(
        path,
        save_all=True,
        append_images=list(frames[1:]),
        duration=[duration] * len(frames),
        loop=0,
        lossless=True,
        method=4,
        exact=True,
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gradient(size: tuple[int, int], top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    width, height = size
    image = Image.new("RGBA", size)
    pixels = image.load()
    for y in range(height):
        ratio = y / max(1, height - 1)
        color = tuple(round(lerp(top[index], bottom[index], ratio)) for index in range(3)) + (255,)
        for x in range(width):
            pixels[x, y] = color
    return image


def decorate_background(image: Image.Image, seed_phase: float = 0.0) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    for band, alpha, amplitude in ((0.76, 22, 6), (0.84, 35, 4), (0.92, 52, 3)):
        points = []
        for x in range(-10, width + 11, 8):
            y = height * band + math.sin(x / 88 + seed_phase + band * 5) * amplitude
            points.append((x, y))
        draw.line(points, fill=(38, 101, 184, alpha), width=2)
    for x, y, r in ((84, 76, 5), (115, 112, 3), (1080, 86, 6), (1110, 130, 3), (1020, 330, 4)):
        if x < width and y < height:
            draw.ellipse((x-r, y-r, x+r, y+r), outline=(38, 101, 184, 62), width=2)


def card_shadow(size: tuple[int, int], radius: int, fill: tuple[int, int, int, int]) -> Image.Image:
    width, height = size
    pad = 24
    layer = Image.new("RGBA", (width + pad * 2, height + pad * 2), (0, 0, 0, 0))
    shadow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    draw.rounded_rectangle((pad, pad + 8, pad + width, pad + height + 8), radius=radius, fill=(24, 53, 92, 35))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle((pad, pad, pad + width, pad + height), radius=radius, fill=fill)
    return Image.alpha_composite(shadow, layer)


def frame_for(frames_by_state: dict[str, list[Image.Image]], spec: StateSpec, index: int | None = None) -> Image.Image:
    frames = frames_by_state[spec.key]
    selected = spec.preview_frame if index is None else index
    return frames[selected % len(frames)]


def build_hero(frames_by_state: dict[str, list[Image.Image]], specs: Sequence[StateSpec]) -> None:
    canvas = gradient((1200, 420), (246, 250, 255), (211, 230, 255))
    decorate_background(canvas)
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle((64, 43, 270, 80), radius=18, fill=(225, 237, 255, 245))
    draw.text((83, 54), "DSH WHALE MOTION · v0.6", font=font(FONT_MEDIUM_CANDIDATES, 15), fill=(27, 83, 165, 255))
    draw.text((64, 110), "Brand-shaped.", font=font(FONT_BOLD_CANDIDATES, 56), fill=(10, 27, 50, 255))
    draw.text((64, 174), "Spine-driven.", font=font(FONT_BOLD_CANDIDATES, 56), fill=(10, 27, 50, 255))
    draw.text((67, 250), "Two original loops are preserved byte-for-byte.", font=font(FONT_REGULAR_CANDIDATES, 21), fill=(65, 82, 109, 255))
    draw.text((67, 280), "Image Gen spout and semantic states share one living whale silhouette.", font=font(FONT_REGULAR_CANDIDATES, 21), fill=(65, 82, 109, 255))
    draw.rounded_rectangle((64, 338, 505, 376), radius=18, fill=(8, 24, 46, 228))
    draw.text((88, 349), "LEGACY SAFE  ·  NO NETWORK  ·  REDUCED MOTION", font=font(FONT_MEDIUM_CANDIDATES, 14), fill=WHITE)

    by_key = {spec.key: spec for spec in specs}
    hero_specs = [by_key[key] for key in ("dive", "classic", "spout", "work")]
    positions = [(690, 48), (872, 48), (690, 218), (872, 218)]
    for (x, y), spec in zip(positions, hero_specs):
        card = card_shadow((156, 136), 24, (255, 255, 255, 244))
        canvas.alpha_composite(card, (x - 24, y - 24))
        whale = frame_for(frames_by_state, spec).resize((112, 112), Image.Resampling.LANCZOS)
        canvas.alpha_composite(whale, (x + 22, y - 4))
        draw.rounded_rectangle((x + 13, y + 102, x + 143, y + 127), radius=12, fill=(236, 244, 255, 255))
        label_font = font(FONT_MEDIUM_CANDIDATES, 11)
        text_box = draw.textbbox((0, 0), spec.label, font=label_font)
        text_width = text_box[2] - text_box[0]
        draw.text((x + 78 - text_width / 2, y + 109), spec.label, font=label_font, fill=(28, 76, 144, 255))
    canvas.convert("RGB").save(DOCS / "hero.png", optimize=True)


def preview_base() -> Image.Image:
    canvas = gradient((1000, 360), (242, 248, 255), (211, 230, 255))
    decorate_background(canvas, 0.7)
    card = card_shadow((824, 210), 30, (255, 255, 255, 247))
    canvas.alpha_composite(card, (64, 48))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle((112, 95, 286, 125), radius=15, fill=(228, 239, 255, 255))
    draw.text((132, 103), "DEEPSEEK HARNESS", font=font(FONT_MEDIUM_CANDIDATES, 12), fill=(28, 84, 168, 255))
    draw.text((112, 146), "Deep diving...", font=font(FONT_MEDIUM_CANDIDATES, 30), fill=(15, 31, 55, 255))
    draw.text((113, 193), "Original loops and brand-aligned states share one director.", font=font(FONT_REGULAR_CANDIDATES, 17), fill=(78, 96, 122, 255))
    draw.rounded_rectangle((210, 309, 790, 338), radius=14, fill=(234, 243, 255, 232))
    draw.text((220, 317), "2 preserved loops  ·  1 Image Gen spout  ·  5 semantic states  ·  static fallbacks", font=font(FONT_MEDIUM_CANDIDATES, 12), fill=(40, 78, 132, 255))
    return canvas


def build_preview(frames_by_state: dict[str, list[Image.Image]], specs: Sequence[StateSpec]) -> None:
    playlist = [spec for spec in specs if spec.playlist]
    rendered: list[Image.Image] = []
    durations: list[int] = []
    segment_frames = 8
    base_template = preview_base()
    for state_index, spec in enumerate(playlist):
        state_frames = frames_by_state[spec.key]
        for local_index in range(segment_frames):
            source_index = round(local_index / segment_frames * len(state_frames)) % len(state_frames)
            frame = base_template.copy()
            whale = state_frames[source_index].resize((210, 210), Image.Resampling.LANCZOS)
            frame.alpha_composite(whale, (665, 61))
            draw = ImageDraw.Draw(frame, "RGBA")
            draw.rounded_rectangle((665, 246, 867, 277), radius=15, fill=(8, 24, 46, 228))
            label_font = font(FONT_MEDIUM_CANDIDATES, 12)
            box = draw.textbbox((0, 0), spec.label, font=label_font)
            draw.text((766 - (box[2] - box[0]) / 2, 255), spec.label, font=label_font, fill=WHITE)
            for pill_index in range(len(playlist)):
                x = 665 + pill_index * 34
                draw.rounded_rectangle((x, 287, x + 25, 293), radius=3, fill=(28, 84, 168, 230 if pill_index == state_index else 52))
            rendered.append(frame.convert("RGBA"))
            durations.append(60)
    rendered[0].save(
        DOCS / "preview.webp",
        save_all=True,
        append_images=rendered[1:],
        duration=durations,
        loop=0,
        quality=78,
        method=3,
        exact=True,
    )


def build_rebuilt_real_speed_preview(frames_by_state: dict[str, list[Image.Image]]) -> None:
    """Render the four rebuilt states together at their actual 40 ms cadence."""
    canvas = gradient((1000, 300), (249, 250, 252), (232, 236, 242))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.text((34, 22), "Black-ink rebuild · real speed", font=font(FONT_BOLD_CANDIDATES, 30), fill=(0, 0, 0, 255))
    draw.text((36, 62), "48 frames · 40 ms per frame · 1.92 s seamless loop", font=font(FONT_REGULAR_CANDIDATES, 15), fill=(74, 83, 98, 255))
    states = (("work", "TOOL RUN"), ("compose", "STREAM"), ("idle", "CALM"), ("alert", "RETRY"))
    x_positions = (24, 268, 512, 756)
    for x, (_, label) in zip(x_positions, states):
        card = card_shadow((220, 186), 22, (255, 255, 255, 246))
        canvas.alpha_composite(card, (x - 24, 86 - 24))
        label_font = font(FONT_MEDIUM_CANDIDATES, 11)
        box = draw.textbbox((0, 0), label, font=label_font)
        draw.text((x + 110 - (box[2] - box[0]) / 2, 247), label, font=label_font, fill=(0, 0, 0, 255))
    rendered: list[Image.Image] = []
    for index in range(FRAMES):
        frame = canvas.copy()
        for x, (state, _) in zip(x_positions, states):
            whale = frames_by_state[state][index % len(frames_by_state[state])].resize((174, 174), Image.Resampling.LANCZOS)
            frame.alpha_composite(whale, (x + 23, 83))
        rendered.append(frame.convert("RGBA"))
    rendered[0].save(
        DOCS / "rebuilt-states-real-speed.webp",
        save_all=True,
        append_images=rendered[1:],
        duration=[FRAME_MS] * FRAMES,
        loop=0,
        quality=86,
        method=4,
        exact=True,
    )


def _wrapped_lines(draw: ImageDraw.ImageDraw, text: str, *, width: int, max_lines: int, text_font: ImageFont.ImageFont) -> list[str]:
    words = text.split()
    lines = [""]
    for word in words:
        candidate = (lines[-1] + " " + word).strip()
        if draw.textlength(candidate, font=text_font) <= width or lines[-1] == "":
            lines[-1] = candidate
        elif len(lines) < max_lines:
            lines.append(word)
        else:
            lines[-1] = lines[-1].rstrip("…") + "…"
            break
    return lines[:max_lines]


def build_gallery(frames_by_state: dict[str, list[Image.Image]], specs: Sequence[StateSpec]) -> None:
    canvas = gradient((1200, 760), (245, 250, 255), (216, 233, 255))
    decorate_background(canvas, 1.4)
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.text((54, 42), "Brand-aligned animation gallery", font=font(FONT_BOLD_CANDIDATES, 40), fill=(8, 24, 46, 255))
    draw.text((56, 95), "Two untouched originals, one Image Gen spout, five semantic states, one shared silhouette.", font=font(FONT_REGULAR_CANDIDATES, 19), fill=(73, 92, 120, 255))

    card_width = 258
    card_height = 240
    x_positions = (42, 329, 616, 903)
    y_positions = (142, 425)
    for index, spec in enumerate(specs):
        row, column = divmod(index, 4)
        x = x_positions[column]
        y = y_positions[row]
        card = card_shadow((card_width, card_height), 26, (255, 255, 255, 245))
        canvas.alpha_composite(card, (x - 24, y - 24))
        whale = frame_for(frames_by_state, spec).resize((132, 132), Image.Resampling.LANCZOS)
        canvas.alpha_composite(whale, (x + 63, y + 4))
        badge_fill = (226, 238, 255, 255) if spec.source == "legacy" else (235, 244, 255, 255)
        draw.rounded_rectangle((x + 18, y + 142, x + card_width - 18, y + 221), radius=18, fill=badge_fill)
        source_label = "PRESERVED" if spec.source == "legacy" else ("IMAGE GEN" if spec.source == "imagegen" else "REDRAWN")
        draw.rounded_rectangle((x + 32, y + 154, x + 101, y + 174), radius=10, fill=(8, 24, 46, 228))
        source_font = font(FONT_MEDIUM_CANDIDATES, 9)
        source_box = draw.textbbox((0, 0), source_label, font=source_font)
        draw.text((x + 66.5 - (source_box[2] - source_box[0]) / 2, y + 160), source_label, font=source_font, fill=WHITE)
        draw.text((x + 112, y + 155), spec.label, font=font(FONT_MEDIUM_CANDIDATES, 11), fill=(27, 72, 137, 255))
        summary_font = font(FONT_REGULAR_CANDIDATES, 10)
        for line_index, line in enumerate(_wrapped_lines(draw, spec.summary, width=190, max_lines=2, text_font=summary_font)):
            draw.text((x + 32, y + 184 + line_index * 13), line, font=summary_font, fill=(72, 91, 119, 255))
    canvas.convert("RGB").save(DOCS / "state-gallery.png", optimize=True)
