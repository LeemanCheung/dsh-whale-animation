from __future__ import annotations

import math
from collections import deque
from functools import lru_cache

from PIL import Image, ImageDraw

from .model import (
    ASSETS,
    CANVAS,
    INK,
    INK_BLACK,
    SUPERSAMPLE,
    StateSpec,
    blank,
    draw_whale,
    finish,
)


LEGACY_REFINED_COMMIT = "65e1205d1fbf4b01997e6dfc099103b0f9717e37"
LEGACY_CLASSIC_COMMIT = "95b06e3f0e6ea817d25858eb29f7064a233b3c65"


@lru_cache(maxsize=2)
def _legacy_ink_frames(state: str) -> tuple[Image.Image, ...]:
    """Load immutable Dive/Classic frames as pure-black RGBA identity masters."""
    source = Image.open(ASSETS / f"whale-{state}.webp")
    frames: list[Image.Image] = []
    for index in range(int(getattr(source, "n_frames", 1))):
        source.seek(index)
        frame = source.convert("RGBA").copy()
        if frame.size != (CANVAS, CANVAS):
            frame = frame.resize((CANVAS, CANVAS), Image.Resampling.LANCZOS)
        ink = Image.new("RGBA", frame.size, INK_BLACK)
        ink.putalpha(frame.getchannel("A"))
        frames.append(ink)
    return tuple(frames)


def _sample_legacy(state: str, position: float) -> Image.Image:
    frames = _legacy_ink_frames(state)
    wrapped = position % len(frames)
    left_index = math.floor(wrapped)
    right_index = (left_index + 1) % len(frames)
    mix = wrapped - left_index
    if mix <= 1e-9:
        return frames[left_index].copy()
    return Image.blend(frames[left_index], frames[right_index], mix)


def _subject_bbox(image: Image.Image) -> tuple[int, int, int, int]:
    """Find the whale while ignoring the long, nearly horizontal waterline."""
    alpha = image.getchannel("A")
    pixels = alpha.load()
    width, height = alpha.size
    row_counts = [sum(pixels[x, y] >= 32 for x in range(width)) for y in range(height)]
    waterline_y = max(range(height), key=row_counts.__getitem__)
    visited: set[tuple[int, int]] = set()
    components: list[list[tuple[int, int]]] = []
    for y in range(height):
        if abs(y - waterline_y) <= 6:
            continue
        for x in range(width):
            if pixels[x, y] < 32 or (x, y) in visited:
                continue
            queue = deque([(x, y)])
            visited.add((x, y))
            component: list[tuple[int, int]] = []
            while queue:
                px, py = queue.popleft()
                component.append((px, py))
                for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                    if (
                        0 <= nx < width
                        and 0 <= ny < height
                        and abs(ny - waterline_y) > 6
                        and pixels[nx, ny] >= 32
                        and (nx, ny) not in visited
                    ):
                        visited.add((nx, ny))
                        queue.append((nx, ny))
            components.append(component)
    if not components:
        return (72, 150, 220, 240)
    subject = max(components, key=len)
    xs = [point[0] for point in subject]
    ys = [point[1] for point in subject]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def render_sonar(t: float) -> Image.Image:
    image = blank()
    phase = math.tau * t
    center = (145 + 5 * math.sin(phase), 178 + 5 * math.sin(phase - 0.4))
    snout = draw_whale(
        image,
        center=center,
        scale=0.82,
        angle=-2.2 + 2.0 * math.sin(phase),
        body_phase=phase,
        tail_phase=phase * 2.0,
        fin_phase=phase,
        wave=10.5,
        bend=4.0 * math.sin(phase - 0.4),
        breathing=0.025 * math.sin(phase),
    )
    draw = ImageDraw.Draw(image, "RGBA")
    for index in range(4):
        progress = (t + index * 0.245) % 1
        radius = 15 + progress * 92
        alpha = round(205 * (1 - progress) ** 1.55)
        box = (
            (snout[0] - radius * 0.25) * SUPERSAMPLE,
            (snout[1] - radius) * SUPERSAMPLE,
            (snout[0] + radius * 1.78) * SUPERSAMPLE,
            (snout[1] + radius) * SUPERSAMPLE,
        )
        draw.arc(
            box,
            start=-43,
            end=43,
            fill=(INK[0], INK[1], INK[2], alpha),
            width=max(2, round((2.35 - progress * 0.75) * SUPERSAMPLE)),
        )
    return finish(image)


def render_work(t: float) -> Image.Image:
    # One complete Refined Dive cycle, retimed from 60 to 48 frames.  The whale,
    # waterline, breach, long-tail flip and re-entry all come from the real loop.
    image = _sample_legacy("dive", t * len(_legacy_ink_frames("dive")))
    phase = math.tau * t
    draw = ImageDraw.Draw(image, "RGBA")
    # A separate speed-stroke layer identifies tool activity without redrawing the body.
    left, top, _, bottom = _subject_bbox(image)
    center_y = (top + bottom) / 2
    for index, offset in enumerate((-9, 0, 9)):
        pulse = 0.5 + 0.5 * math.sin(phase * 2 + index * 1.4)
        x2 = max(24, left - 5 - index * 3)
        y = center_y + offset
        length = 24 + 18 * pulse
        draw.line(
            ((x2 - length, y), (x2, y + math.sin(phase + index) * 2)),
            fill=(0, 0, 0, round(130 + 95 * pulse)),
            width=3,
        )
    return image


def render_compose(t: float) -> Image.Image:
    # Ping-pong through Classic's underwater tail-first arc (frames 240..360).
    # Cosine timing reaches each end with zero velocity and returns without a cut.
    phase = math.tau * t
    position = 300.0 - 60.0 * math.cos(phase)
    image = _sample_legacy("classic", position)
    draw = ImageDraw.Draw(image, "RGBA")
    for index in range(4):
        progress = (t + index * 0.22) % 1
        x = 260 + 54 * progress
        y = 118 - 24 * math.sin(progress * math.pi) + 3 * math.sin(phase + index)
        radius = 1.4 + (1 - progress) * 1.5
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=(0, 0, 0, round(165 * (1 - progress))),
        )
    return image


def render_idle(t: float) -> Image.Image:
    # A gentle pass across Dive frames 45..65 (wrapping through the original
    # seam) preserves its waterline and long-tail underwater turn.
    phase = math.tau * t
    position = 55.0 - 10.0 * math.cos(phase)
    return _sample_legacy("dive", position)


def render_alert(t: float) -> Image.Image:
    # Classic frames 88..170 contain a real surface curl into a sudden spy-hop.
    # The return leg reuses the same full-body silhouettes in reverse for recoil.
    phase = math.tau * t
    pulse = 0.5 - 0.5 * math.cos(phase)
    position = 129.0 - 41.0 * math.cos(phase)
    image = _sample_legacy("classic", position)
    draw = ImageDraw.Draw(image, "RGBA")
    for index, angle in enumerate((-38, -8, 22)):
        radians = math.radians(angle)
        inner = 16 + index * 2
        outer = inner + 5 + 10 * pulse
        anchor = (253, 113)
        start = (anchor[0] + math.cos(radians) * inner, anchor[1] + math.sin(radians) * inner)
        end = (anchor[0] + math.cos(radians) * outer, anchor[1] + math.sin(radians) * outer)
        draw.line(
            (start, end),
            fill=(0, 0, 0, round(35 + 190 * pulse)),
            width=2,
        )
    return image


def state_specs() -> list[StateSpec]:
    return [
        StateSpec(
            "dive",
            "REFINED DIVE",
            "The v0.3 refined loop, retained byte-for-byte",
            None,
            preview_frame=28,
            source="legacy",
            preserved_from=LEGACY_REFINED_COMMIT,
        ),
        StateSpec(
            "classic",
            "CLASSIC",
            "The first published loop, retained byte-for-byte",
            None,
            preview_frame=20,
            source="legacy",
            preserved_from=LEGACY_CLASSIC_COMMIT,
        ),
        StateSpec(
            "spout",
            "SURFACE SPOUT",
            "Complete Refined Dive followed by a 77-frame Image Gen surface-spout act",
            None,
            preview_frame=101,
            source="imagegen",
            derived_from=("whale-dive.webp", "artwork-sources/spout-imagegen-v1"),
        ),
        StateSpec(
            "sonar",
            "SONAR",
            "Spine-driven cruise with expanding discovery rings",
            render_sonar,
            preview_frame=22,
        ),
        StateSpec(
            "work",
            "TOOL RUN",
            "Retimed Refined Dive breach, long-tail flip and re-entry with speed strokes",
            render_work,
            preview_frame=18,
            derived_from=("whale-dive.webp",),
        ),
        StateSpec(
            "compose",
            "STREAM",
            "Classic tail-first underwater S-curve with a restrained output-droplet arc",
            render_compose,
            preview_frame=12,
            derived_from=("whale-classic.webp",),
        ),
        StateSpec(
            "idle",
            "CALM",
            "Refined Dive waterline hover with a gentle long-tail turn",
            render_idle,
            preview_frame=12,
            derived_from=("whale-dive.webp",),
        ),
        StateSpec(
            "alert",
            "RETRY",
            "Classic surface curl into a sudden spy-hop and full-body recoil",
            render_alert,
            playlist=False,
            preview_frame=24,
            derived_from=("whale-classic.webp",),
        ),
    ]
