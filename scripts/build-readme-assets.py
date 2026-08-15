from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets' / 'whale-dive.webp'
DOCS = ROOT / 'docs'
HERO = DOCS / 'hero.png'
PREVIEW = DOCS / 'preview.webp'
SCREENSHOTS = DOCS / 'screenshots'
DOCS.mkdir(exist_ok=True)
SCREENSHOTS.mkdir(exist_ok=True)

FONT_REGULAR = Path(r'C:\Windows\Fonts\segoeui.ttf')
FONT_SEMIBOLD = Path(r'C:\Windows\Fonts\seguisb.ttf')
FONT_BOLD = Path(r'C:\Windows\Fonts\segoeuib.ttf')


def font(path, size):
    if path.exists():
        return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def gradient(size, top, bottom):
    width, height = size
    a = np.array(top, dtype=np.float32)
    b = np.array(bottom, dtype=np.float32)
    rows = np.linspace(0, 1, height, dtype=np.float32)[:, None, None]
    pixels = a[None, None, :] * (1 - rows) + b[None, None, :] * rows
    pixels = np.repeat(pixels, width, axis=1).astype(np.uint8)
    return Image.fromarray(pixels, 'RGB').convert('RGBA')


def rounded_card(size, radius, fill, shadow_blur=22, shadow_offset=8):
    width, height = size
    layer = Image.new('RGBA', (width + shadow_blur * 2, height + shadow_blur * 2 + shadow_offset), (0, 0, 0, 0))
    shadow = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow)
    box = (shadow_blur, shadow_blur + shadow_offset, shadow_blur + width, shadow_blur + shadow_offset + height)
    draw.rounded_rectangle(box, radius=radius, fill=(31, 56, 96, 45))
    shadow = shadow.filter(ImageFilter.GaussianBlur(shadow_blur // 2))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle((shadow_blur, shadow_blur, shadow_blur + width, shadow_blur + height), radius=radius, fill=fill)
    return Image.alpha_composite(shadow, layer)


def decorate_background(image, compact=False):
    draw = ImageDraw.Draw(image)
    width, height = image.size
    # Calm water bands and bubbles echo the animation without competing with it.
    bands = ((0.86, 36), (0.92, 24), (0.98, 18)) if compact else ((0.84, 36), (0.91, 24), (0.98, 18))
    for band, alpha in bands:
        points = []
        y0 = int(height * band)
        for x in range(0, width + 8, 8):
            y = y0 + math.sin(x / width * math.pi * 5 + band * 8) * (4 if compact else 7)
            points.append((x, y))
        draw.line(points, fill=(44, 111, 199, alpha), width=2 if compact else 3)
    bubbles = [(0.08, 0.25, 5), (0.13, 0.34, 3), (0.90, 0.18, 4), (0.94, 0.29, 7), (0.84, 0.77, 4)]
    for bx, by, radius in bubbles:
        x, y = int(width * bx), int(height * by)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=(31, 94, 181, 70), width=2)


def source_frames():
    image = Image.open(SOURCE)
    frames, delays = [], []
    for index in range(image.n_frames):
        image.seek(index)
        frames.append(image.convert('RGBA').copy())
        delays.append(int(image.info.get('duration') or 33))
    return frames, delays


def build_hero(frames):
    canvas = gradient((1200, 380), (245, 250, 255), (218, 235, 255))
    decorate_background(canvas)
    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle((70, 54, 248, 92), radius=19, fill=(226, 238, 255, 235))
    draw.text((91, 64), 'DSH WEB PLUGIN', font=font(FONT_SEMIBOLD, 17), fill=(25, 83, 167, 255))
    draw.text((70, 120), 'Whale dive,', font=font(FONT_BOLD, 58), fill=(15, 30, 54, 255))
    draw.text((70, 185), 'without the hard cut.', font=font(FONT_BOLD, 58), fill=(15, 30, 54, 255))
    draw.text((73, 276), 'A persistent animated status companion for DeepSeek Harness.', font=font(FONT_REGULAR, 25), fill=(66, 84, 112, 255))

    card = rounded_card((300, 270), 36, (255, 255, 255, 242), shadow_blur=28, shadow_offset=12)
    canvas.alpha_composite(card, (820, 48))
    # A mid-leap frame gives the static hero a clear dynamic silhouette.
    whale = frames[24 % len(frames)].resize((255, 255), Image.Resampling.LANCZOS)
    canvas.alpha_composite(whale, (870, 66))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((872, 306, 1067, 338), radius=16, fill=(15, 30, 54, 220))
    draw.text((894, 313), 'SEAMLESS CLOSED LOOP', font=font(FONT_SEMIBOLD, 14), fill='white')
    canvas.convert('RGB').save(HERO, optimize=True)


def preview_base():
    canvas = gradient((1000, 320), (239, 247, 255), (213, 231, 253))
    decorate_background(canvas, compact=True)
    card = rounded_card((780, 160), 28, (255, 255, 255, 246), shadow_blur=22, shadow_offset=8)
    canvas.alpha_composite(card, (88, 68))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((126, 103, 276, 133), radius=15, fill=(230, 239, 253, 255))
    draw.text((145, 109), 'DEEPSEEK HARNESS', font=font(FONT_SEMIBOLD, 13), fill=(34, 90, 174, 255))
    draw.text((128, 151), 'Deep diving...', font=font(FONT_SEMIBOLD, 30), fill=(22, 35, 55, 255))
    draw.text((128, 196), 'The real embedded animation, shown beside the turn status.', font=font(FONT_REGULAR, 17), fill=(91, 107, 132, 255))
    draw.rounded_rectangle((280, 264, 720, 298), radius=17, fill=(238, 246, 255, 235))
    draw.text((320, 272), '60 native frames   •   33 ms/frame   •   reduced-motion fallback', font=font(FONT_SEMIBOLD, 16), fill=(43, 79, 130, 255))
    return canvas


def build_preview(frames, delays):
    base = preview_base()
    rendered, rendered_delays = [], []
    # The production asset is already a compact 60-frame, ~30 fps loop, so the
    # README preview preserves every native drawing and its exact timing.
    for index in range(len(frames)):
        frame = base.copy()
        whale = frames[index].resize((184, 184), Image.Resampling.LANCZOS)
        frame.alpha_composite(whale, (642, 58))
        rendered.append(frame.convert('RGBA'))
        rendered_delays.append(delays[index])
    rendered[0].save(
        PREVIEW,
        save_all=True,
        append_images=rendered[1:],
        duration=rendered_delays,
        loop=0,
        lossless=True,
        method=6,
        exact=True,
    )


def build_stage_screenshots(frames):
    stages = [
        ('01', 'BREACH', 'Powering through the waterline', 17, 'launch.png'),
        ('02', 'APEX', 'Body curl and tail follow-through', 24, 'apex.png'),
        ('03', 'DEEP DIVE', 'Returning below the surface', 47, 'deep-dive.png'),
    ]
    for number, title, caption, frame_index, filename in stages:
        canvas = gradient((900, 520), (241, 248, 255), (214, 232, 254))
        decorate_background(canvas)
        draw = ImageDraw.Draw(canvas)
        draw.rounded_rectangle((42, 36, 858, 474), radius=34, fill=(255, 255, 255, 246))
        draw.rounded_rectangle((74, 70, 135, 106), radius=18, fill=(224, 237, 255, 255))
        draw.text((92, 77), number, font=font(FONT_BOLD, 17), fill=(25, 83, 167, 255))
        draw.text((74, 132), title, font=font(FONT_BOLD, 44), fill=(15, 30, 54, 255))
        draw.text((76, 190), caption, font=font(FONT_REGULAR, 21), fill=(78, 96, 123, 255))
        draw.rounded_rectangle((74, 250, 390, 330), radius=22, fill=(239, 246, 255, 255))
        draw.text((100, 269), 'Deep diving...', font=font(FONT_SEMIBOLD, 29), fill=(22, 35, 55, 255))
        draw.text((77, 402), f'Rendered from source frame {frame_index + 1} / {len(frames)}', font=font(FONT_SEMIBOLD, 16), fill=(43, 79, 130, 255))
        whale = frames[frame_index].resize((330, 330), Image.Resampling.LANCZOS)
        canvas.alpha_composite(whale, (500, 105))
        canvas.convert('RGB').save(SCREENSHOTS / filename, optimize=True)


def main():
    frames, delays = source_frames()
    if len(frames) != 60 or set(delays) != {33}:
        raise RuntimeError(f'Unexpected animation source: {len(frames)} frames, delays={sorted(set(delays))}')
    build_hero(frames)
    build_preview(frames, delays)
    build_stage_screenshots(frames)
    print({
        'hero': str(HERO),
        'heroBytes': HERO.stat().st_size,
        'preview': str(PREVIEW),
        'previewBytes': PREVIEW.stat().st_size,
        'previewFrames': len(frames),
        'screenshots': [str(path) for path in sorted(SCREENSHOTS.glob('*.png'))],
    })


if __name__ == '__main__':
    main()
