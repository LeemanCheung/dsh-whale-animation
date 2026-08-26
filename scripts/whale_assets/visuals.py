from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFilter

from .model import (
    DOCS, FONT_BOLD_CANDIDATES, FONT_MEDIUM_CANDIDATES,
    FONT_REGULAR_CANDIDATES, FRAME_MS, FRAMES, INK, StateSpec, WHITE, font, lerp,
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
    for band, alpha, amplitude in ((0.76, 24, 6), (0.84, 38, 4), (0.92, 56, 3)):
        points = []
        for x in range(-10, width + 11, 8):
            y = height * band + math.sin(x / 88 + seed_phase + band * 5) * amplitude
            points.append((x, y))
        draw.line(points, fill=(48, 109, 190, alpha), width=2)
    for x, y, r in ((84, 76, 5), (115, 112, 3), (1080, 86, 6), (1110, 130, 3), (1020, 330, 4)):
        if x < width and y < height:
            draw.ellipse((x-r, y-r, x+r, y+r), outline=(48, 109, 190, 65), width=2)


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


def render_on_card(frame: Image.Image, size: int) -> Image.Image:
    return frame.resize((size, size), Image.Resampling.LANCZOS)


def build_hero(frames_by_state: dict[str, list[Image.Image]], specs: Sequence[StateSpec]) -> None:
    canvas = gradient((1200, 420), (245, 250, 255), (214, 232, 255))
    decorate_background(canvas)
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle((64, 44, 244, 80), radius=18, fill=(226, 238, 255, 245))
    draw.text((83, 54), "DSH WEB PLUGIN", font=font(FONT_MEDIUM_CANDIDATES, 15), fill=(31, 91, 177, 255))
    draw.text((64, 111), "Six states.", font=font(FONT_BOLD_CANDIDATES, 58), fill=(14, 29, 52, 255))
    draw.text((64, 176), "One living whale.", font=font(FONT_BOLD_CANDIDATES, 58), fill=(14, 29, 52, 255))
    draw.text((67, 251), "A reactive animation director for", font=font(FONT_REGULAR_CANDIDATES, 23), fill=(70, 87, 113, 255))
    draw.text((67, 281), "long-running DeepSeek Harness turns.", font=font(FONT_REGULAR_CANDIDATES, 23), fill=(70, 87, 113, 255))
    draw.rounded_rectangle((64, 339, 467, 375), radius=18, fill=(15, 30, 54, 225))
    draw.text((88, 349), "NO NETWORK  ·  THEME AWARE  ·  REDUCED MOTION", font=font(FONT_MEDIUM_CANDIDATES, 14), fill=WHITE)

    positions = [(692, 48), (872, 48), (692, 218), (872, 218)]
    hero_specs = [specs[0], specs[1], specs[2], specs[3]]
    for (x, y), spec in zip(positions, hero_specs):
        card = card_shadow((154, 136), 24, (255, 255, 255, 244))
        canvas.alpha_composite(card, (x - 24, y - 24))
        whale = render_on_card(frames_by_state[spec.key][spec.preview_frame], 108)
        canvas.alpha_composite(whale, (x + 23, y - 2))
        draw.rounded_rectangle((x + 14, y + 102, x + 140, y + 126), radius=12, fill=(237, 245, 255, 255))
        text_box = draw.textbbox((0, 0), spec.label, font=font(FONT_MEDIUM_CANDIDATES, 12))
        text_width = text_box[2] - text_box[0]
        draw.text((x + 77 - text_width / 2, y + 108), spec.label, font=font(FONT_MEDIUM_CANDIDATES, 12), fill=(31, 80, 146, 255))
    canvas.convert("RGB").save(DOCS / "hero.png", optimize=True)


def preview_base() -> Image.Image:
    canvas = gradient((1000, 360), (241, 248, 255), (214, 232, 255))
    decorate_background(canvas, 0.7)
    card = card_shadow((824, 210), 30, (255, 255, 255, 247))
    canvas.alpha_composite(card, (64, 48))
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.rounded_rectangle((112, 95, 264, 125), radius=15, fill=(229, 240, 255, 255))
    draw.text((132, 103), "DEEPSEEK HARNESS", font=font(FONT_MEDIUM_CANDIDATES, 12), fill=(31, 91, 177, 255))
    draw.text((112, 146), "Deep diving...", font=font(FONT_MEDIUM_CANDIDATES, 30), fill=(18, 34, 57, 255))
    draw.text((113, 193), "The director changes motion without changing your UI.", font=font(FONT_REGULAR_CANDIDATES, 17), fill=(83, 100, 125, 255))
    draw.rounded_rectangle((242, 310, 758, 338), radius=14, fill=(235, 244, 255, 230))
    draw.text((279, 317), "5-state playlist  ·  keyword overrides  ·  static reduced-motion frames", font=font(FONT_MEDIUM_CANDIDATES, 13), fill=(45, 82, 134, 255))
    return canvas


def build_preview(frames_by_state: dict[str, list[Image.Image]], specs: Sequence[StateSpec]) -> None:
    playlist = [spec for spec in specs if spec.playlist]
    rendered: list[Image.Image] = []
    durations: list[int] = []
    segment_frames = 10
    base_template = preview_base()
    for state_index, spec in enumerate(playlist):
        for local_index in range(segment_frames):
            source_index = round(local_index / segment_frames * FRAMES) % FRAMES
            frame = base_template.copy()
            whale = frames_by_state[spec.key][source_index].resize((208, 208), Image.Resampling.LANCZOS)
            frame.alpha_composite(whale, (665, 62))
            draw = ImageDraw.Draw(frame, "RGBA")
            draw.rounded_rectangle((665, 246, 865, 276), radius=15, fill=(15, 30, 54, 225))
            label_font = font(FONT_MEDIUM_CANDIDATES, 13)
            box = draw.textbbox((0, 0), spec.label, font=label_font)
            draw.text((765 - (box[2] - box[0]) / 2, 254), spec.label, font=label_font, fill=WHITE)
            # Progress pills show that the preview is a sequence, not one asset.
            for pill_index in range(len(playlist)):
                x = 668 + pill_index * 40
                draw.rounded_rectangle((x, 287, x + 30, 293), radius=3, fill=(31, 91, 177, 230 if pill_index == state_index else 55))
            rendered.append(frame.convert("RGBA"))
            durations.append(55)
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


def build_gallery(frames_by_state: dict[str, list[Image.Image]], specs: Sequence[StateSpec]) -> None:
    canvas = gradient((1200, 760), (244, 250, 255), (218, 234, 255))
    decorate_background(canvas, 1.4)
    draw = ImageDraw.Draw(canvas, "RGBA")
    draw.text((64, 46), "Animation state gallery", font=font(FONT_BOLD_CANDIDATES, 42), fill=(15, 30, 54, 255))
    draw.text((66, 101), "Five automatic playlist states plus one error/retry override.", font=font(FONT_REGULAR_CANDIDATES, 20), fill=(78, 95, 121, 255))
    for index, spec in enumerate(specs):
        row, column = divmod(index, 3)
        x = 54 + column * 382
        y = 154 + row * 274
        card = card_shadow((330, 226), 28, (255, 255, 255, 245))
        canvas.alpha_composite(card, (x - 24, y - 24))
        whale = frames_by_state[spec.key][spec.preview_frame].resize((154, 154), Image.Resampling.LANCZOS)
        canvas.alpha_composite(whale, (x + 88, y + 2))
        draw.rounded_rectangle((x + 24, y + 158, x + 306, y + 207), radius=18, fill=(235, 244, 255, 255))
        draw.text((x + 42, y + 166), spec.label, font=font(FONT_MEDIUM_CANDIDATES, 13), fill=(31, 80, 146, 255))
        summary_font = font(FONT_REGULAR_CANDIDATES, 11)
        words = spec.summary.split()
        lines = [""]
        for word in words:
            candidate = (lines[-1] + " " + word).strip()
            if draw.textlength(candidate, font=summary_font) <= 245 or lines[-1] == "":
                lines[-1] = candidate
            elif len(lines) == 1:
                lines.append(word)
            else:
                lines[-1] += "…"
                break
        for line_index, line in enumerate(lines[:2]):
            draw.text((x + 42, y + 184 + line_index * 13), line, font=summary_font, fill=(76, 94, 121, 255))
    canvas.convert("RGB").save(DOCS / "state-gallery.png", optimize=True)
