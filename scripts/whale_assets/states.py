from __future__ import annotations

import math

from PIL import Image, ImageDraw

from .model import (
    FRAMES, INK, SUPERSAMPLE, StateSpec, blank, draw_bubbles, draw_splash,
    draw_water, draw_whale, finish, transform,
)

def render_idle(t: float) -> Image.Image:
    image = blank()
    phase = math.tau * t
    center = (176 + 5 * math.sin(phase), 180 + 8 * math.sin(phase - 0.35))
    draw_whale(image, center=center, scale=0.82, angle=2.8 * math.sin(phase), tail_phase=phase * 2, fin_phase=phase, eye_open=0.65 + 0.35 * (0.5 + 0.5 * math.sin(phase - 0.5)))
    bubbles = []
    for index in range(4):
        progress = (t + index * 0.23) % 1
        bubbles.append((238 + 7 * math.sin(progress * math.tau + index), 176 - 105 * progress, 2.3 + index * 0.7, 180 * (1 - progress)))
    draw_bubbles(image, bubbles)
    return finish(image)


def render_dive(t: float) -> Image.Image:
    image = blank()
    phase = math.tau * t
    water_y = 210
    # Clockwise closed loop: submerged cruise -> breach -> inverted apex -> dive.
    cx = 176 + 76 * math.sin(phase)
    cy = 190 + 86 * math.cos(phase)
    dx = 76 * math.cos(phase)
    dy = -86 * math.sin(phase)
    angle = math.degrees(math.atan2(dy, dx))
    draw_water(image, water_y, phase * 1.8, 0.65)
    # Entry/exit splashes sit behind the body so facial details stay legible.
    for crossing in (0.20, 0.80):
        delta = min(abs(t - crossing), 1 - abs(t - crossing))
        intensity = max(0.0, 1 - delta / 0.075)
        draw_splash(image, cx, water_y + 2, intensity, -1 if crossing < 0.5 else 1)
    draw_whale(image, center=(cx, cy), scale=0.72, angle=angle, tail_phase=phase * 3.1, fin_phase=phase * 1.4)
    return finish(image)


def render_sonar(t: float) -> Image.Image:
    image = blank()
    phase = math.tau * t
    center = (148 + 6 * math.sin(phase), 178 + 7 * math.sin(phase * 1.5))
    snout = draw_whale(image, center=center, scale=0.78, angle=-3 + 3 * math.sin(phase), tail_phase=phase * 1.8, fin_phase=phase * 0.8)
    draw = ImageDraw.Draw(image, "RGBA")
    for index in range(4):
        progress = (t * 1.25 + index * 0.24) % 1
        radius = 18 + progress * 93
        alpha = round(210 * (1 - progress) ** 1.6)
        box = ((snout[0] - radius * 0.25) * SUPERSAMPLE, (snout[1] - radius) * SUPERSAMPLE, (snout[0] + radius * 1.75) * SUPERSAMPLE, (snout[1] + radius) * SUPERSAMPLE)
        draw.arc(box, start=-48, end=48, fill=(INK[0], INK[1], INK[2], alpha), width=max(2, round((2.5 - progress) * SUPERSAMPLE)))
    return finish(image)


def render_work(t: float) -> Image.Image:
    image = blank()
    phase = math.tau * t
    center = (184 + 10 * math.sin(phase), 180 + 4 * math.sin(phase * 2))
    draw = ImageDraw.Draw(image, "RGBA")
    for index in range(7):
        progress = (t * 1.9 + index / 7) % 1
        x1 = 122 - progress * 92
        y = 128 + index * 18 + 5 * math.sin(phase + index)
        length = 18 + 34 * (1 - progress)
        alpha = round(170 * (1 - progress))
        draw.line(((x1 - length) * SUPERSAMPLE, y * SUPERSAMPLE, x1 * SUPERSAMPLE, y * SUPERSAMPLE), fill=(INK[0], INK[1], INK[2], alpha), width=max(2, round(1.6 * SUPERSAMPLE)))
    draw_whale(image, center=center, scale=0.80, angle=1.5 * math.sin(phase * 2), tail_phase=phase * 4.2, fin_phase=phase * 2.5)
    # Orbiting work particles read as gears without tiny detailed iconography.
    for index in range(3):
        a = phase * 1.6 + index * math.tau / 3
        x = 265 + math.cos(a) * (17 + index * 2)
        y = 167 + math.sin(a) * (17 + index * 2)
        r = 2.8 + index * 0.7
        draw.regular_polygon((x * SUPERSAMPLE, y * SUPERSAMPLE, r * SUPERSAMPLE), n_sides=6, rotation=math.degrees(a), fill=(INK[0], INK[1], INK[2], 150))
    return finish(image)


def render_compose(t: float) -> Image.Image:
    image = blank()
    phase = math.tau * t
    center = (157 + 5 * math.sin(phase), 181 + 7 * math.sin(phase * 1.2))
    snout = draw_whale(image, center=center, scale=0.78, angle=-2.5 + 2 * math.sin(phase), tail_phase=phase * 2.2, fin_phase=phase)
    draw = ImageDraw.Draw(image, "RGBA")
    shapes = ("circle", "square", "circle", "diamond", "square")
    for index, shape in enumerate(shapes):
        progress = (t * 0.95 + index * 0.19) % 1
        x = snout[0] + 16 + 112 * progress
        y = snout[1] - 14 - 25 * math.sin(progress * math.pi) + 5 * math.sin(index + phase)
        size = 4.8 - progress * 1.8
        alpha = round(210 * (1 - progress) ** 0.7)
        bounds = ((x - size) * SUPERSAMPLE, (y - size) * SUPERSAMPLE, (x + size) * SUPERSAMPLE, (y + size) * SUPERSAMPLE)
        if shape == "circle":
            draw.ellipse(bounds, fill=(INK[0], INK[1], INK[2], alpha))
        elif shape == "square":
            draw.rounded_rectangle(bounds, radius=max(1, round(size * 0.5 * SUPERSAMPLE)), fill=(INK[0], INK[1], INK[2], alpha))
        else:
            draw.polygon(transform([(0, -size), (size, 0), (0, size), (-size, 0)], x, y, 1, 0), fill=(INK[0], INK[1], INK[2], alpha))
    return finish(image)


def render_alert(t: float) -> Image.Image:
    image = blank()
    phase = math.tau * t
    pulse = 0.5 + 0.5 * math.sin(phase * 2)
    center = (169 + 5 * math.sin(phase * 2), 185 + 3 * math.cos(phase * 2))
    draw_whale(image, center=center, scale=0.78, angle=7 * math.sin(phase * 2), tail_phase=phase * 3.1, fin_phase=phase * 2, eye_open=1)
    draw = ImageDraw.Draw(image, "RGBA")
    bubble_center = (263, 109)
    radius = 27 + 7 * pulse
    draw.ellipse(((bubble_center[0] - radius) * SUPERSAMPLE, (bubble_center[1] - radius) * SUPERSAMPLE, (bubble_center[0] + radius) * SUPERSAMPLE, (bubble_center[1] + radius) * SUPERSAMPLE), outline=(INK[0], INK[1], INK[2], round(100 + 120 * pulse)), width=max(3, round(2.5 * SUPERSAMPLE)))
    draw.rounded_rectangle(((bubble_center[0] - 3.2) * SUPERSAMPLE, (bubble_center[1] - 13) * SUPERSAMPLE, (bubble_center[0] + 3.2) * SUPERSAMPLE, (bubble_center[1] + 6) * SUPERSAMPLE), radius=2 * SUPERSAMPLE, fill=INK)
    draw.ellipse(((bubble_center[0] - 3.4) * SUPERSAMPLE, (bubble_center[1] + 12) * SUPERSAMPLE, (bubble_center[0] + 3.4) * SUPERSAMPLE, (bubble_center[1] + 18.8) * SUPERSAMPLE), fill=INK)
    return finish(image)


def state_specs() -> list[StateSpec]:
    return [
        StateSpec("dive", "DEEP DIVE", "Breach, roll and return below the surface", render_dive, preview_frame=28),
        StateSpec("sonar", "SONAR", "Expanding echolocation rings for discovery", render_sonar, preview_frame=22),
        StateSpec("work", "TOOL RUN", "Fast tail cadence, speed trails and work particles", render_work, preview_frame=17),
        StateSpec("compose", "STREAM", "Token-like particles flow from the whale's path", render_compose, preview_frame=23),
        StateSpec("idle", "CALM", "Low-motion breathing loop for waiting periods", render_idle, preview_frame=13),
        StateSpec("alert", "RETRY", "A restrained attention pulse for errors or retries", render_alert, playlist=False, preview_frame=16),
    ]
