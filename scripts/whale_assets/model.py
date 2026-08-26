from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
DOCS = ROOT / "docs"
CANVAS = 352
SUPERSAMPLE = 2
FRAMES = 48
FRAME_MS = 40
INK = (8, 20, 36, 255)
WHITE = (255, 255, 255, 255)

FONT_REGULAR_CANDIDATES = (
    Path("/usr/share/fonts/opentype/inter/InterDisplay-Regular.otf"),
    Path("/usr/share/fonts/truetype/lato/Lato-Regular.ttf"),
    Path(r"C:\Windows\Fonts\segoeui.ttf"),
)
FONT_MEDIUM_CANDIDATES = (
    Path("/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf"),
    Path("/usr/share/fonts/truetype/lato/Lato-Medium.ttf"),
    Path(r"C:\Windows\Fonts\seguisb.ttf"),
)
FONT_BOLD_CANDIDATES = (
    Path("/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf"),
    Path("/usr/share/fonts/truetype/lato/Lato-Bold.ttf"),
    Path(r"C:\Windows\Fonts\segoeuib.ttf"),
)


@dataclass(frozen=True)
class StateSpec:
    key: str
    label: str
    summary: str
    render: Callable[[float], Image.Image]
    playlist: bool = True
    preview_frame: int = 18


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def font(candidates: Sequence[Path], size: int) -> ImageFont.ImageFont:
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def cubic(p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float], steps: int = 12) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(steps):
        t = index / steps
        u = 1 - t
        points.append((
            u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1],
        ))
    return points


def transform(points: Iterable[tuple[float, float]], cx: float, cy: float, scale: float, angle_deg: float) -> list[tuple[int, int]]:
    angle = math.radians(angle_deg)
    cosine, sine = math.cos(angle), math.sin(angle)
    result = []
    for x, y in points:
        result.append((
            round((cx + (x * cosine - y * sine) * scale) * SUPERSAMPLE),
            round((cy + (x * sine + y * cosine) * scale) * SUPERSAMPLE),
        ))
    return result


def point_transform(point: tuple[float, float], cx: float, cy: float, scale: float, angle_deg: float) -> tuple[float, float]:
    angle = math.radians(angle_deg)
    cosine, sine = math.cos(angle), math.sin(angle)
    x, y = point
    return (
        cx + (x * cosine - y * sine) * scale,
        cy + (x * sine + y * cosine) * scale,
    )


def blank() -> Image.Image:
    return Image.new("RGBA", (CANVAS * SUPERSAMPLE, CANVAS * SUPERSAMPLE), (0, 0, 0, 0))


def finish(image: Image.Image) -> Image.Image:
    return image.resize((CANVAS, CANVAS), Image.Resampling.LANCZOS)


def draw_whale(
    image: Image.Image,
    *,
    center: tuple[float, float],
    scale: float,
    angle: float,
    tail_phase: float,
    fin_phase: float,
    opacity: int = 255,
    eye_open: float = 1.0,
) -> tuple[float, float]:
    """Draw a compact articulated whale and return its world-space snout point."""
    draw = ImageDraw.Draw(image, "RGBA")
    cx, cy = center
    ink = (INK[0], INK[1], INK[2], opacity)
    white = (255, 255, 255, opacity)

    body: list[tuple[float, float]] = []
    body += cubic((84, -2), (78, -22), (52, -37), (12, -40), 14)
    body += cubic((12, -40), (-22, -43), (-58, -29), (-77, -10), 14)
    body += cubic((-77, -10), (-83, -2), (-81, 7), (-70, 15), 8)
    body += cubic((-70, 15), (-42, 39), (14, 45), (54, 29), 16)
    body += cubic((54, 29), (75, 21), (86, 10), (84, -2), 10)
    draw.polygon(transform(body, cx, cy, scale, angle), fill=ink)

    dorsal = [(-30, -34), (-14, -62), (2, -38), (-8, -30)]
    draw.polygon(transform(dorsal, cx, cy, scale, angle), fill=ink)

    fin_extension = 12 * math.sin(fin_phase)
    fin = [(18, 27), (4, 65 + fin_extension), (-12, 54 + fin_extension * 0.45), (-3, 24)]
    draw.polygon(transform(fin, cx, cy, scale, angle), fill=ink)

    tail_wave = 14 * math.sin(tail_phase)
    tail_twist = 7 * math.sin(tail_phase + math.pi / 2)
    peduncle = [
        (-72, -8),
        (-104, tail_wave - 6),
        (-126, tail_wave + tail_twist - 3),
        (-126, tail_wave + tail_twist + 4),
        (-103, tail_wave + 7),
        (-69, 11),
    ]
    draw.polygon(transform(peduncle, cx, cy, scale, angle), fill=ink)
    tail_end = (-126, tail_wave + tail_twist)
    upper_fluke = [tail_end, (-148, tail_wave - 25), (-177, tail_wave - 19), (-153, tail_wave + 2)]
    lower_fluke = [tail_end, (-149, tail_wave + 23), (-177, tail_wave + 18), (-153, tail_wave - 1)]
    draw.polygon(transform(upper_fluke, cx, cy, scale, angle), fill=ink)
    draw.polygon(transform(lower_fluke, cx, cy, scale, angle), fill=ink)

    eye = point_transform((55, -16), cx, cy, scale, angle)
    eye_radius_x = max(1.7, 3.1 * scale)
    eye_radius_y = max(0.8, 2.3 * scale * max(0.15, eye_open))
    draw.ellipse(
        (
            (eye[0] - eye_radius_x) * SUPERSAMPLE,
            (eye[1] - eye_radius_y) * SUPERSAMPLE,
            (eye[0] + eye_radius_x) * SUPERSAMPLE,
            (eye[1] + eye_radius_y) * SUPERSAMPLE,
        ),
        fill=white,
    )
    pupil = point_transform((56, -16), cx, cy, scale, angle)
    pr = max(0.6, 1.1 * scale)
    draw.ellipse(((pupil[0] - pr) * SUPERSAMPLE, (pupil[1] - pr) * SUPERSAMPLE, (pupil[0] + pr) * SUPERSAMPLE, (pupil[1] + pr) * SUPERSAMPLE), fill=ink)

    mouth = transform([(54, 9), (64, 11), (75, 8), (82, 4)], cx, cy, scale, angle)
    draw.line(mouth, fill=white, width=max(2, round(1.7 * scale * SUPERSAMPLE)), joint="curve")
    throat = transform([(38, 25), (45, 30), (53, 28)], cx, cy, scale, angle)
    draw.line(throat, fill=(255, 255, 255, max(100, opacity - 45)), width=max(1, round(scale * SUPERSAMPLE)))
    return point_transform((84, -2), cx, cy, scale, angle)


def draw_bubbles(image: Image.Image, points: Sequence[tuple[float, float, float, float]]) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    for x, y, radius, alpha in points:
        draw.ellipse(
            ((x - radius) * SUPERSAMPLE, (y - radius) * SUPERSAMPLE, (x + radius) * SUPERSAMPLE, (y + radius) * SUPERSAMPLE),
            outline=(INK[0], INK[1], INK[2], round(alpha)),
            width=max(2, round(radius * 0.42 * SUPERSAMPLE)),
        )


def draw_water(image: Image.Image, y: float, phase: float, strength: float = 1.0) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    points = []
    for x in range(-10, CANVAS + 11, 4):
        amplitude = 2.4 + 2.0 * strength
        wave = math.sin(x / 26 + phase) * amplitude + math.sin(x / 51 - phase * 0.7) * 1.4
        points.append((x * SUPERSAMPLE, (y + wave) * SUPERSAMPLE))
    draw.line(points, fill=(INK[0], INK[1], INK[2], round(115 + 70 * strength)), width=max(2, round(2.1 * SUPERSAMPLE)))


def draw_splash(image: Image.Image, x: float, y: float, intensity: float, direction: float) -> None:
    if intensity <= 0:
        return
    draw = ImageDraw.Draw(image, "RGBA")
    alpha = round(220 * min(1, intensity))
    for index, offset in enumerate((-22, -10, 0, 12, 24)):
        height = (13 + (index % 3) * 7) * intensity
        drift = direction * (5 + index * 2) * intensity
        start = ((x + offset) * SUPERSAMPLE, y * SUPERSAMPLE)
        end = ((x + offset + drift) * SUPERSAMPLE, (y - height) * SUPERSAMPLE)
        draw.line((start, end), fill=(INK[0], INK[1], INK[2], alpha), width=max(2, round(1.6 * SUPERSAMPLE)))
        radius = 1.7 + index % 2
        draw.ellipse(((end[0] - radius * SUPERSAMPLE), (end[1] - radius * SUPERSAMPLE), (end[0] + radius * SUPERSAMPLE), (end[1] + radius * SUPERSAMPLE)), fill=(INK[0], INK[1], INK[2], alpha))
