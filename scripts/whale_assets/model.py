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
SUPERSAMPLE = 3
FRAMES = 48
FRAME_MS = 40
INK = (3, 18, 38, 255)
INK_BLACK = (0, 0, 0, 255)
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
    render: Callable[[float], Image.Image] | None
    playlist: bool = True
    preview_frame: int = 18
    source: str = "generated"
    preserved_from: str | None = None
    derived_from: tuple[str, ...] | None = None


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def smoothstep(value: float) -> float:
    t = clamp(value)
    return t * t * (3 - 2 * t)


def font(candidates: Sequence[Path], size: int) -> ImageFont.ImageFont:
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def cubic(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    p3: tuple[float, float],
    steps: int = 12,
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for index in range(steps):
        t = index / steps
        u = 1 - t
        points.append((
            u ** 3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t ** 3 * p3[0],
            u ** 3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t ** 3 * p3[1],
        ))
    return points


def transform(
    points: Iterable[tuple[float, float]],
    cx: float,
    cy: float,
    scale: float,
    angle_deg: float,
) -> list[tuple[int, int]]:
    angle = math.radians(angle_deg)
    cosine, sine = math.cos(angle), math.sin(angle)
    result = []
    for x, y in points:
        result.append((
            round((cx + (x * cosine - y * sine) * scale) * SUPERSAMPLE),
            round((cy + (x * sine + y * cosine) * scale) * SUPERSAMPLE),
        ))
    return result


def point_transform(
    point: tuple[float, float],
    cx: float,
    cy: float,
    scale: float,
    angle_deg: float,
) -> tuple[float, float]:
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


def _radius_profile(s: float, breathing: float) -> tuple[float, float]:
    """DeepSeek-like silhouette: narrow peduncle, full torso, domed melon, blunt snout."""
    if s < 0.18:
        radius = lerp(5.5, 12.0, smoothstep(s / 0.18))
    elif s < 0.48:
        radius = lerp(12.0, 35.0, smoothstep((s - 0.18) / 0.30))
    elif s < 0.73:
        radius = lerp(35.0, 43.0, smoothstep((s - 0.48) / 0.25))
    else:
        radius = lerp(43.0, 27.5, smoothstep((s - 0.73) / 0.27))
    body_weight = math.sin(math.pi * clamp(s)) ** 1.35
    radius *= 1 + breathing * body_weight
    melon = math.exp(-((s - 0.82) / 0.19) ** 2)
    top = radius * (1.0 + 0.10 * melon)
    bottom = radius * (1.0 - 0.08 * melon)
    return top, bottom


def _centerline(
    s: float,
    *,
    body_phase: float,
    tail_phase: float,
    wave: float,
    bend: float,
    stretch: float,
) -> tuple[float, float]:
    # Tail motion propagates forward but the head remains calm and recognizable.
    x = -112 + 194 * stretch * s
    tail_weight = (1 - s) ** 1.65
    torso_weight = (1 - s) ** 0.70
    travelling = math.sin(body_phase - (1 - s) * math.pi * 2.15)
    tail_flick = math.sin(tail_phase - (1 - s) * math.pi * 0.85)
    y = wave * (0.18 + 0.82 * tail_weight) * travelling
    y += wave * 0.30 * tail_weight * tail_flick
    y += bend * math.sin(math.pi * s) * (0.25 + 0.75 * torso_weight)
    return x, y


def _frame_at(
    s: float,
    *,
    body_phase: float,
    tail_phase: float,
    wave: float,
    bend: float,
    stretch: float,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    delta = 0.003
    p = _centerline(s, body_phase=body_phase, tail_phase=tail_phase, wave=wave, bend=bend, stretch=stretch)
    before = _centerline(max(0, s - delta), body_phase=body_phase, tail_phase=tail_phase, wave=wave, bend=bend, stretch=stretch)
    after = _centerline(min(1, s + delta), body_phase=body_phase, tail_phase=tail_phase, wave=wave, bend=bend, stretch=stretch)
    dx, dy = after[0] - before[0], after[1] - before[1]
    length = max(1e-6, math.hypot(dx, dy))
    tangent = (dx / length, dy / length)
    normal = (-tangent[1], tangent[0])
    return p, tangent, normal


def _offset(
    point: tuple[float, float],
    tangent: tuple[float, float],
    normal: tuple[float, float],
    along: float,
    across: float,
) -> tuple[float, float]:
    return (
        point[0] + tangent[0] * along + normal[0] * across,
        point[1] + tangent[1] * along + normal[1] * across,
    )


def draw_whale(
    image: Image.Image,
    *,
    center: tuple[float, float],
    scale: float,
    angle: float,
    body_phase: float,
    tail_phase: float,
    fin_phase: float,
    wave: float = 10.0,
    bend: float = 0.0,
    stretch: float = 1.0,
    breathing: float = 0.0,
    opacity: int = 255,
    eye_open: float = 1.0,
) -> tuple[float, float]:
    """Draw a spine-driven DeepSeek-brand whale and return its world-space snout point.

    The silhouette intentionally avoids fish/shark cues: there is no dorsal fin, the
    head is melon-shaped and blunt, the caudal peduncle is long and flexible, and
    the flukes are two broad leaf forms. Motion is derived from the centerline so
    the torso flexes as one living body instead of rotating rigid polygons.
    """
    draw = ImageDraw.Draw(image, "RGBA")
    cx, cy = center
    ink = (INK[0], INK[1], INK[2], opacity)
    white = (255, 255, 255, opacity)

    samples = 52
    centerline = []
    tangents = []
    normals = []
    top_points: list[tuple[float, float]] = []
    bottom_points: list[tuple[float, float]] = []
    for index in range(samples + 1):
        s = index / samples
        p, tangent, normal = _frame_at(
            s,
            body_phase=body_phase,
            tail_phase=tail_phase,
            wave=wave,
            bend=bend,
            stretch=stretch,
        )
        top_radius, bottom_radius = _radius_profile(s, breathing)
        centerline.append(p)
        tangents.append(tangent)
        normals.append(normal)
        top_points.append(_offset(p, tangent, normal, 0, -top_radius))
        bottom_points.append(_offset(p, tangent, normal, 0, bottom_radius))

    # Round the forehead and snout with an ellipse-like forward cap.
    head = centerline[-1]
    head_tangent = tangents[-1]
    head_normal = normals[-1]
    head_top, head_bottom = _radius_profile(1.0, breathing)
    cap_points: list[tuple[float, float]] = []
    for index in range(17):
        theta = -math.pi / 2 + math.pi * index / 16
        along = math.cos(theta) * 24.5
        across_radius = head_top if theta < 0 else head_bottom
        cap_points.append(_offset(head, head_tangent, head_normal, along, math.sin(theta) * across_radius))

    body = top_points + cap_points[1:-1] + list(reversed(bottom_points))
    draw.polygon(transform(body, cx, cy, scale, angle), fill=ink)

    # Small pectoral fin; compact and swept back like the DeepSeek mark.
    fin_s = 0.61
    fin_point, fin_tangent, fin_normal = _frame_at(
        fin_s,
        body_phase=body_phase,
        tail_phase=tail_phase,
        wave=wave,
        bend=bend,
        stretch=stretch,
    )
    _, fin_bottom = _radius_profile(fin_s, breathing)
    fin_swing = 5.5 * math.sin(fin_phase)
    fin = [
        _offset(fin_point, fin_tangent, fin_normal, -8, fin_bottom * 0.50),
        _offset(fin_point, fin_tangent, fin_normal, -18, fin_bottom + 19 + fin_swing),
        _offset(fin_point, fin_tangent, fin_normal, 5, fin_bottom + 31 + fin_swing * 0.45),
        _offset(fin_point, fin_tangent, fin_normal, 15, fin_bottom * 0.58),
    ]
    draw.polygon(transform(fin, cx, cy, scale, angle), fill=ink)

    # Broad whale flukes; two rounded leaves rather than a fish tail.
    tail = centerline[0]
    tail_tangent = tangents[0]
    tail_normal = normals[0]
    tail_twist = 3.5 * math.sin(tail_phase + math.pi / 2)
    upper_fluke = [
        _offset(tail, tail_tangent, tail_normal, 2, -1),
        _offset(tail, tail_tangent, tail_normal, -15, -5),
        _offset(tail, tail_tangent, tail_normal, -35, -26 - tail_twist),
        _offset(tail, tail_tangent, tail_normal, -56, -21 - tail_twist),
        _offset(tail, tail_tangent, tail_normal, -43, -3),
        _offset(tail, tail_tangent, tail_normal, -13, 4),
    ]
    lower_fluke = [
        _offset(tail, tail_tangent, tail_normal, 2, 1),
        _offset(tail, tail_tangent, tail_normal, -15, 5),
        _offset(tail, tail_tangent, tail_normal, -35, 25 - tail_twist),
        _offset(tail, tail_tangent, tail_normal, -56, 19 - tail_twist),
        _offset(tail, tail_tangent, tail_normal, -43, 3),
        _offset(tail, tail_tangent, tail_normal, -13, -4),
    ]
    draw.polygon(transform(upper_fluke, cx, cy, scale, angle), fill=ink)
    draw.polygon(transform(lower_fluke, cx, cy, scale, angle), fill=ink)

    # Eye: a clean white dot with a dark pupil, anchored to the bending head.
    eye_s = 0.88
    eye_point, eye_tangent, eye_normal = _frame_at(
        eye_s,
        body_phase=body_phase,
        tail_phase=tail_phase,
        wave=wave,
        bend=bend,
        stretch=stretch,
    )
    eye_top, _ = _radius_profile(eye_s, breathing)
    eye_local = _offset(eye_point, eye_tangent, eye_normal, 5.0, -eye_top * 0.36)
    eye_world = point_transform(eye_local, cx, cy, scale, angle)
    eye_radius_x = max(1.6, 3.0 * scale)
    eye_radius_y = max(0.7, 2.2 * scale * max(0.12, eye_open))
    draw.ellipse(
        (
            (eye_world[0] - eye_radius_x) * SUPERSAMPLE,
            (eye_world[1] - eye_radius_y) * SUPERSAMPLE,
            (eye_world[0] + eye_radius_x) * SUPERSAMPLE,
            (eye_world[1] + eye_radius_y) * SUPERSAMPLE,
        ),
        fill=white,
    )
    pupil_local = _offset(eye_local, eye_tangent, eye_normal, 0.9, 0.2)
    pupil_world = point_transform(pupil_local, cx, cy, scale, angle)
    pupil_radius = max(0.55, 1.0 * scale)
    draw.ellipse(
        (
            (pupil_world[0] - pupil_radius) * SUPERSAMPLE,
            (pupil_world[1] - pupil_radius) * SUPERSAMPLE,
            (pupil_world[0] + pupil_radius) * SUPERSAMPLE,
            (pupil_world[1] + pupil_radius) * SUPERSAMPLE,
        ),
        fill=ink,
    )

    # A restrained curved mouth line, matching the logo's friendly but not cartoonish expression.
    mouth_points: list[tuple[float, float]] = []
    for index, s in enumerate((0.84, 0.89, 0.94, 0.985)):
        p, tangent, normal = _frame_at(
            s,
            body_phase=body_phase,
            tail_phase=tail_phase,
            wave=wave,
            bend=bend,
            stretch=stretch,
        )
        _, bottom_radius = _radius_profile(s, breathing)
        mouth_points.append(_offset(p, tangent, normal, 4 + index * 1.5, bottom_radius * (0.34 - index * 0.025)))
    draw.line(
        transform(mouth_points, cx, cy, scale, angle),
        fill=white,
        width=max(2, round(1.55 * scale * SUPERSAMPLE)),
        joint="curve",
    )

    throat_points: list[tuple[float, float]] = []
    for s, along in ((0.73, -2), (0.78, 1), (0.83, 4)):
        p, tangent, normal = _frame_at(
            s,
            body_phase=body_phase,
            tail_phase=tail_phase,
            wave=wave,
            bend=bend,
            stretch=stretch,
        )
        _, bottom_radius = _radius_profile(s, breathing)
        throat_points.append(_offset(p, tangent, normal, along, bottom_radius * 0.70))
    draw.line(
        transform(throat_points, cx, cy, scale, angle),
        fill=(255, 255, 255, max(90, opacity - 65)),
        width=max(1, round(0.95 * scale * SUPERSAMPLE)),
        joint="curve",
    )

    snout_local = _offset(head, head_tangent, head_normal, 24.5, 0)
    return point_transform(snout_local, cx, cy, scale, angle)


def _ink_radius_profile(s: float, breathing: float) -> tuple[float, float]:
    """Slender ink-whale profile derived from the preserved Dive/Classic loops.

    Unlike the compact logo-like profile above, this silhouette keeps almost half
    of its length in a narrow, flexible tail stock.  That long taper and the broad
    flukes remain legible after the artwork is reduced to the 60 px UI size.
    """
    if s < 0.30:
        radius = lerp(2.8, 4.2, smoothstep(s / 0.30))
    elif s < 0.48:
        radius = lerp(4.2, 12.5, smoothstep((s - 0.30) / 0.18))
    elif s < 0.68:
        radius = lerp(12.5, 27.5, smoothstep((s - 0.48) / 0.20))
    elif s < 0.88:
        radius = lerp(27.5, 30.5, smoothstep((s - 0.68) / 0.20))
    else:
        radius = lerp(30.5, 20.0, smoothstep((s - 0.88) / 0.12))
    body_weight = math.sin(math.pi * clamp(s)) ** 1.45
    radius *= 1 + breathing * body_weight
    melon = math.exp(-((s - 0.89) / 0.14) ** 2)
    return radius * (1.0 + 0.08 * melon), radius * (1.0 - 0.07 * melon)


def _ink_centerline(
    s: float,
    *,
    body_phase: float,
    tail_phase: float,
    wave: float,
    bend: float,
    stretch: float,
) -> tuple[float, float]:
    x = -126 + 206 * stretch * s
    tail_weight = (1 - s) ** 1.40
    torso_weight = (1 - s) ** 0.58
    travelling = math.sin(body_phase - (1 - s) * math.pi * 1.85)
    tail_flick = math.sin(tail_phase - (1 - s) * math.pi * 0.72)
    y = wave * (0.12 + 0.88 * tail_weight) * travelling
    y += wave * 0.44 * tail_weight * tail_flick
    y += bend * math.sin(math.pi * s) * (0.18 + 0.82 * torso_weight)
    return x, y


def _ink_frame_at(
    s: float,
    *,
    body_phase: float,
    tail_phase: float,
    wave: float,
    bend: float,
    stretch: float,
) -> tuple[tuple[float, float], tuple[float, float], tuple[float, float]]:
    delta = 0.003
    kwargs = {
        "body_phase": body_phase,
        "tail_phase": tail_phase,
        "wave": wave,
        "bend": bend,
        "stretch": stretch,
    }
    point = _ink_centerline(s, **kwargs)
    before = _ink_centerline(max(0, s - delta), **kwargs)
    after = _ink_centerline(min(1, s + delta), **kwargs)
    dx, dy = after[0] - before[0], after[1] - before[1]
    length = max(1e-6, math.hypot(dx, dy))
    tangent = (dx / length, dy / length)
    normal = (-tangent[1], tangent[0])
    return point, tangent, normal


def draw_ink_whale(
    image: Image.Image,
    *,
    center: tuple[float, float],
    scale: float,
    angle: float,
    body_phase: float,
    tail_phase: float,
    fin_phase: float,
    wave: float = 13.0,
    bend: float = 0.0,
    stretch: float = 1.0,
    breathing: float = 0.0,
    eye_open: float = 1.0,
) -> tuple[float, float]:
    """Draw the black ink character used by Work/Compose/Idle/Alert.

    Its identity comes from the preserved Dive/Classic motion language: a small
    blunt head, sharply tapered living torso, long narrow tail stock, broad leaf
    flukes, one quiet pectoral fin, and no dorsal-fin/fish-tail cues.
    """
    draw = ImageDraw.Draw(image, "RGBA")
    cx, cy = center
    ink = INK_BLACK
    samples = 64
    centerline: list[tuple[float, float]] = []
    tangents: list[tuple[float, float]] = []
    normals: list[tuple[float, float]] = []
    top_points: list[tuple[float, float]] = []
    bottom_points: list[tuple[float, float]] = []
    for index in range(samples + 1):
        s = index / samples
        point, tangent, normal = _ink_frame_at(
            s,
            body_phase=body_phase,
            tail_phase=tail_phase,
            wave=wave,
            bend=bend,
            stretch=stretch,
        )
        top_radius, bottom_radius = _ink_radius_profile(s, breathing)
        centerline.append(point)
        tangents.append(tangent)
        normals.append(normal)
        top_points.append(_offset(point, tangent, normal, 0, -top_radius))
        bottom_points.append(_offset(point, tangent, normal, 0, bottom_radius))

    head = centerline[-1]
    head_tangent = tangents[-1]
    head_normal = normals[-1]
    head_top, head_bottom = _ink_radius_profile(1.0, breathing)
    cap_points: list[tuple[float, float]] = []
    for index in range(19):
        theta = -math.pi / 2 + math.pi * index / 18
        along = math.cos(theta) * 22.0
        radius = head_top if theta < 0 else head_bottom
        cap_points.append(_offset(head, head_tangent, head_normal, along, math.sin(theta) * radius))
    draw.polygon(
        transform(top_points + cap_points[1:-1] + list(reversed(bottom_points)), cx, cy, scale, angle),
        fill=ink,
    )

    fin_s = 0.70
    fin_point, fin_tangent, fin_normal = _ink_frame_at(
        fin_s,
        body_phase=body_phase,
        tail_phase=tail_phase,
        wave=wave,
        bend=bend,
        stretch=stretch,
    )
    _, fin_bottom = _ink_radius_profile(fin_s, breathing)
    fin_swing = 4.5 * math.sin(fin_phase)
    fin = [
        _offset(fin_point, fin_tangent, fin_normal, -8, fin_bottom * 0.48),
        _offset(fin_point, fin_tangent, fin_normal, -15, fin_bottom + 12 + fin_swing),
        _offset(fin_point, fin_tangent, fin_normal, 1, fin_bottom + 26 + fin_swing * 0.55),
        _offset(fin_point, fin_tangent, fin_normal, 13, fin_bottom * 0.58),
    ]
    draw.polygon(transform(fin, cx, cy, scale, angle), fill=ink)

    tail = centerline[0]
    tail_tangent = tangents[0]
    tail_normal = normals[0]
    tail_twist = 3.8 * math.sin(tail_phase + math.pi / 2)
    upper_fluke = [
        _offset(tail, tail_tangent, tail_normal, 2, -1),
        _offset(tail, tail_tangent, tail_normal, -12, -4),
        _offset(tail, tail_tangent, tail_normal, -31, -22 - tail_twist),
        _offset(tail, tail_tangent, tail_normal, -49, -19 - tail_twist),
        _offset(tail, tail_tangent, tail_normal, -38, -2),
        _offset(tail, tail_tangent, tail_normal, -12, 3),
    ]
    lower_fluke = [
        _offset(tail, tail_tangent, tail_normal, 2, 1),
        _offset(tail, tail_tangent, tail_normal, -12, 4),
        _offset(tail, tail_tangent, tail_normal, -31, 21 - tail_twist),
        _offset(tail, tail_tangent, tail_normal, -49, 18 - tail_twist),
        _offset(tail, tail_tangent, tail_normal, -38, 2),
        _offset(tail, tail_tangent, tail_normal, -12, -3),
    ]
    draw.polygon(transform(upper_fluke, cx, cy, scale, angle), fill=ink)
    draw.polygon(transform(lower_fluke, cx, cy, scale, angle), fill=ink)

    eye_s = 0.91
    eye_point, eye_tangent, eye_normal = _ink_frame_at(
        eye_s,
        body_phase=body_phase,
        tail_phase=tail_phase,
        wave=wave,
        bend=bend,
        stretch=stretch,
    )
    eye_top, _ = _ink_radius_profile(eye_s, breathing)
    eye_local = _offset(eye_point, eye_tangent, eye_normal, 4.0, -eye_top * 0.31)
    eye_world = point_transform(eye_local, cx, cy, scale, angle)
    eye_radius_x = max(1.45, 2.8 * scale)
    eye_radius_y = max(0.65, 2.0 * scale * max(0.12, eye_open))
    draw.ellipse(
        (
            (eye_world[0] - eye_radius_x) * SUPERSAMPLE,
            (eye_world[1] - eye_radius_y) * SUPERSAMPLE,
            (eye_world[0] + eye_radius_x) * SUPERSAMPLE,
            (eye_world[1] + eye_radius_y) * SUPERSAMPLE,
        ),
        fill=WHITE,
    )
    pupil_local = _offset(eye_local, eye_tangent, eye_normal, 0.8, 0.2)
    pupil_world = point_transform(pupil_local, cx, cy, scale, angle)
    pupil_radius = max(0.55, 1.0 * scale)
    draw.ellipse(
        (
            (pupil_world[0] - pupil_radius) * SUPERSAMPLE,
            (pupil_world[1] - pupil_radius) * SUPERSAMPLE,
            (pupil_world[0] + pupil_radius) * SUPERSAMPLE,
            (pupil_world[1] + pupil_radius) * SUPERSAMPLE,
        ),
        fill=ink,
    )

    mouth_points: list[tuple[float, float]] = []
    for index, s in enumerate((0.89, 0.93, 0.965, 0.992)):
        point, tangent, normal = _ink_frame_at(
            s,
            body_phase=body_phase,
            tail_phase=tail_phase,
            wave=wave,
            bend=bend,
            stretch=stretch,
        )
        _, bottom_radius = _ink_radius_profile(s, breathing)
        mouth_points.append(_offset(point, tangent, normal, 3 + index, bottom_radius * (0.30 - index * 0.015)))
    draw.line(
        transform(mouth_points, cx, cy, scale, angle),
        fill=WHITE,
        width=max(1, round(1.05 * scale * SUPERSAMPLE)),
        joint="curve",
    )

    snout_local = _offset(head, head_tangent, head_normal, 22.0, 0)
    return point_transform(snout_local, cx, cy, scale, angle)


def draw_bubbles(image: Image.Image, points: Sequence[tuple[float, float, float, float]]) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    for x, y, radius, alpha in points:
        draw.ellipse(
            ((x - radius) * SUPERSAMPLE, (y - radius) * SUPERSAMPLE, (x + radius) * SUPERSAMPLE, (y + radius) * SUPERSAMPLE),
            outline=(INK[0], INK[1], INK[2], round(alpha)),
            width=max(2, round(radius * 0.40 * SUPERSAMPLE)),
        )


def draw_water(image: Image.Image, y: float, phase: float, strength: float = 1.0) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    points = []
    for x in range(-10, CANVAS + 11, 4):
        amplitude = 2.0 + 1.9 * strength
        wave = math.sin(x / 27 + phase) * amplitude + math.sin(x / 55 - phase * 0.7) * 1.2
        points.append((x * SUPERSAMPLE, (y + wave) * SUPERSAMPLE))
    draw.line(points, fill=(INK[0], INK[1], INK[2], round(110 + 65 * strength)), width=max(2, round(1.8 * SUPERSAMPLE)))


def draw_splash(image: Image.Image, x: float, y: float, intensity: float, direction: float) -> None:
    if intensity <= 0:
        return
    draw = ImageDraw.Draw(image, "RGBA")
    alpha = round(215 * min(1, intensity))
    for index, offset in enumerate((-22, -10, 0, 12, 24)):
        height = (12 + (index % 3) * 6) * intensity
        drift = direction * (5 + index * 2) * intensity
        start = ((x + offset) * SUPERSAMPLE, y * SUPERSAMPLE)
        end = ((x + offset + drift) * SUPERSAMPLE, (y - height) * SUPERSAMPLE)
        draw.line((start, end), fill=(INK[0], INK[1], INK[2], alpha), width=max(2, round(1.45 * SUPERSAMPLE)))
        radius = 1.5 + index % 2
        draw.ellipse(
            ((end[0] - radius * SUPERSAMPLE), (end[1] - radius * SUPERSAMPLE), (end[0] + radius * SUPERSAMPLE), (end[1] + radius * SUPERSAMPLE)),
            fill=(INK[0], INK[1], INK[2], alpha),
        )
