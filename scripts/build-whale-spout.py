from collections import deque
from pathlib import Path
import hashlib
import json
import math

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
SPRITES = ROOT / 'artwork-sources' / 'spout-imagegen-v1'
PHASES = (
    SPRITES / 'phase-1-rise.png',
    SPRITES / 'phase-2-grow.png',
    SPRITES / 'phase-3-fall.png',
    SPRITES / 'phase-4-submerge.png',
)
DIVE = ASSETS / 'whale-dive.webp'
RUNTIME = ASSETS / 'whale-spout.webp'
RUNTIME_STATIC = ASSETS / 'whale-spout.png'
CONTACT = SPRITES / 'native-contact.png'
REPORT = SPRITES / 'build-report.json'
SIZE = 352
GRID = 4
CELLS_PER_PHASE = 16
DIVE_FRAMES = 60
NATIVE_CELS = len(PHASES) * CELLS_PER_PHASE
BOUNDARY_INBETWEENS = 2
FRAME_MS = 33
WATER_Y = 160
LINE_RADIUS = 10
HANDOFF_CELLS = 4
INBOUND_HANDOFF_FRAMES = HANDOFF_CELLS - 1
OUTBOUND_HANDOFF_FRAMES = HANDOFF_CELLS


def clamp(value, low=0.0, high=1.0):
    return max(low, min(high, value))


def smoothstep(value):
    value = clamp(value)
    return value * value * (3.0 - 2.0 * value)


def black_rgba(alpha):
    out = np.zeros((alpha.shape[0], alpha.shape[1], 4), dtype=np.uint8)
    out[:, :, 3] = alpha
    return Image.fromarray(out, 'RGBA')


def ink_alpha(image):
    # Image Gen may return opaque white or transparent PNGs. Composite both on
    # white, then convert only dark marks to a black alpha channel. White belly,
    # eye, and mouth cutouts remain transparent inside the moving silhouette.
    source = image.convert('RGBA')
    white = Image.new('RGBA', source.size, 'white')
    white.alpha_composite(source)
    rgb = np.asarray(white.convert('RGB'), dtype=np.uint8)
    lum = (
        rgb[:, :, 0].astype(np.float32) * 0.2126
        + rgb[:, :, 1].astype(np.float32) * 0.7152
        + rgb[:, :, 2].astype(np.float32) * 0.0722
    )
    return np.clip((246.0 - lum) * 255.0 / 224.0, 0, 255).astype(np.uint8)


def crop_cells(path):
    image = Image.open(path).convert('RGBA')
    width, height = image.size
    if width < 900 or height < 900:
        raise RuntimeError(f'{path.name} is too small for a 4x4 sheet: {image.size}')
    sheet_alpha = ink_alpha(image)
    sheet_lines = detect_sheet_waterlines(sheet_alpha)
    cells = []
    for index in range(CELLS_PER_PHASE):
        col, row = index % GRID, index // GRID
        left, right = round(col * width / GRID), round((col + 1) * width / GRID)
        top, bottom = round(row * height / GRID), round((row + 1) * height / GRID)
        alpha = ink_alpha(image.crop((left, top, right, bottom)))
        resized = Image.fromarray(alpha, 'L').resize((SIZE, SIZE), Image.Resampling.LANCZOS)
        local_line = (sheet_lines[row][0] - top) * SIZE / max(1, bottom - top)
        cells.append({
            'alpha': np.asarray(resized, dtype=np.uint8).copy(),
            'lineY': round(local_line),
            'lineRun': sheet_lines[row][1],
        })
    return image.size, cells


def longest_run(values):
    best = current = 0
    for value in values:
        if value:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def detect_sheet_waterlines(alpha):
    """Find one global horizontal water band for each conceptual sheet row.

    GPT Image 2 sometimes drifts a row's local waterline upward across the 4x4
    canvas. Detecting on the complete sheet remains reliable because each band
    spans almost the full 1254 px width, unlike any whale body.
    """
    height, width = alpha.shape
    visible = alpha > 18
    results = []
    cell_height = height / GRID
    radius = max(3, round(height / 300))
    for row in range(GRID):
        low = max(0, round(row * cell_height - cell_height * 0.15))
        high = min(height - 1, round(row * cell_height + cell_height * 0.70))
        best_y, best_coverage = -1, -1
        for y in range(low, high + 1):
            columns = visible[max(0, y - radius):min(height, y + radius + 1)].any(axis=0)
            coverage = int(columns.sum())
            if coverage > best_coverage:
                best_y, best_coverage = y, coverage
        if best_y < 0 or best_coverage < round(width * 0.65):
            raise RuntimeError(f'Could not detect sheet-row waterline {row + 1}: y={best_y}, coverage={best_coverage}')
        results.append((best_y, best_coverage))
    return results


def detect_waterline(alpha, expected=None):
    visible = alpha > 32
    if expected is None:
        low, high = round(SIZE * 0.10), round(SIZE * 0.58)
    else:
        low, high = max(0, expected - 55), min(SIZE - 1, expected + 55)
    best_y, best_run = -1, -1
    radius = 4
    for y in range(low, high + 1):
        columns = visible[max(0, y - radius):min(SIZE, y + radius + 1)].any(axis=0)
        run = longest_run(columns)
        if run > best_run:
            best_y, best_run = y, run
    if best_y < 0 or best_run < round(SIZE * 0.45):
        raise RuntimeError(f'Could not detect a stable waterline: y={best_y}, run={best_run}')
    return best_y, best_run


def remove_waterline(alpha, y):
    moving = alpha.copy()
    moving[max(0, y - LINE_RADIUS):min(SIZE, y + LINE_RADIUS + 1), :] = 0
    return moving


def largest_component(alpha, threshold=72, include_mask=False):
    mask = (alpha >= threshold).reshape(-1)
    seen = np.zeros(mask.shape[0], dtype=bool)
    width = alpha.shape[1]
    height = alpha.shape[0]
    best = None
    for seed in np.flatnonzero(mask):
        if seen[seed]:
            continue
        queue = deque([int(seed)])
        seen[seed] = True
        pixels = []
        sx = sy = 0
        min_x = width
        min_y = height
        max_x = max_y = -1
        while queue:
            point = queue.popleft()
            pixels.append(point)
            x, y = point % width, point // width
            sx += x
            sy += y
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            if x > 0:
                neighbours = (point - 1,)
            else:
                neighbours = ()
            if x + 1 < width:
                neighbours += (point + 1,)
            if y > 0:
                neighbours += (point - width,)
            if y + 1 < height:
                neighbours += (point + width,)
            for neighbour in neighbours:
                if mask[neighbour] and not seen[neighbour]:
                    seen[neighbour] = True
                    queue.append(neighbour)
        area = len(pixels)
        candidate = {
            'area': area,
            'cx': sx / area,
            'cy': sy / area,
            'bbox': [min_x, min_y, max_x, max_y],
            'width': max_x - min_x + 1,
            'height': max_y - min_y + 1,
        }
        if best is None or area > best['area']:
            if include_mask:
                component = np.zeros(mask.shape[0], dtype=np.uint8)
                component[pixels] = 255
                candidate['mask'] = component.reshape((height, width))
            best = candidate
    if best is None or best['area'] < 250:
        raise RuntimeError('A sprite cell has no substantial whale component')
    return best


def waterline_from(frame):
    alpha = np.asarray(frame.convert('RGBA'), dtype=np.uint8)[:, :, 3]
    line = np.zeros_like(alpha)
    line[max(0, WATER_Y - 12):min(SIZE, WATER_Y + 13)] = alpha[
        max(0, WATER_Y - 12):min(SIZE, WATER_Y + 13)
    ]
    return line


def target_for(index, old_body):
    phase, local = divmod(index, CELLS_PER_PHASE)
    q = local / (CELLS_PER_PHASE - 1)
    old_center = np.array([old_body['cx'], old_body['cy']], dtype=np.float32)
    surface_center = np.array([181.0, 194.0], dtype=np.float32)
    if phase == 0:
        amount = smoothstep(q)
        center = old_center * (1 - amount) + surface_center * amount
    elif phase == 1:
        center = surface_center + np.array([
            math.sin(q * math.tau) * 2.4,
            math.sin(q * math.tau * 2.0 + 0.4) * 2.2,
        ])
    elif phase == 2:
        center = surface_center + np.array([
            math.sin(q * math.tau + 0.7) * 2.0,
            math.sin(q * math.tau * 2.0 + 1.2) * 2.5,
        ])
    else:
        amount = smoothstep(q)
        center = surface_center * (1 - amount) + old_center * amount
    breathing = 1.0 + (0.035 * math.sin(index / NATIVE_CELS * math.tau * 3.0) if phase in (1, 2) else 0.0)
    return center, old_body['area'] * breathing


def transform_moving(alpha, source_body, target_center, target_area):
    scale = math.sqrt(target_area / source_body['area'])
    scale = clamp(scale, 0.42, 1.75)
    offset_x = target_center[0] - scale * source_body['cx']
    offset_y = target_center[1] - scale * source_body['cy']
    inverse = (
        1.0 / scale,
        0.0,
        -offset_x / scale,
        0.0,
        1.0 / scale,
        -offset_y / scale,
    )
    moved = black_rgba(alpha).transform(
        (SIZE, SIZE),
        Image.Transform.AFFINE,
        inverse,
        resample=Image.Resampling.BICUBIC,
    )
    return np.asarray(moved, dtype=np.uint8)[:, :, 3].copy(), scale


def normalize_native_cells(raw_cells, old_body, canonical_line):
    frames = []
    details = []
    for index, cell in enumerate(raw_cells):
        alpha = cell['alpha']
        detected_y, line_run = cell['lineY'], cell['lineRun']
        moving = remove_waterline(alpha, detected_y)
        source_body = largest_component(moving)
        target_center, target_area = target_for(index, old_body)
        moved, scale = transform_moving(moving, source_body, target_center, target_area)
        composed = np.maximum(moved, canonical_line)
        frames.append(black_rgba(composed))
        details.append({
            'frame': index + 1,
            'phase': index // CELLS_PER_PHASE + 1,
            'sourceWaterlineY': detected_y,
            'sourceWaterlineRun': line_run,
            'sourceBody': {key: source_body[key] for key in ('area', 'cx', 'cy', 'bbox', 'width', 'height')},
            'targetCenter': [float(target_center[0]), float(target_center[1])],
            'targetArea': float(target_area),
            'scale': float(scale),
        })
    return frames, details


def alpha_morph(left, right, amount):
    if amount <= 0:
        return left.copy()
    if amount >= 1:
        return right.copy()
    a = np.asarray(left.convert('RGBA'), dtype=np.float32)[:, :, 3]
    b = np.asarray(right.convert('RGBA'), dtype=np.float32)[:, :, 3]
    mixed = a * (1 - amount) + b * amount
    solid = np.clip((mixed - 12.0) * 255.0 / 228.0, 0, 255).astype(np.uint8)
    return black_rgba(solid)


def assemble_native_phases(native):
    """Keep every generated cel and add short phase-boundary morphs.

    The accepted dive workflow used dedicated bridge art at cross-sheet seams.
    Here two contrast-preserving in-betweens make each of the three sheet
    boundaries continuous without replacing or dropping any native body pose.
    """
    output = list(native[:CELLS_PER_PHASE])
    for phase in range(1, len(PHASES)):
        start = phase * CELLS_PER_PHASE
        previous = output[-1]
        following = native[start]
        for step in range(1, BOUNDARY_INBETWEENS + 1):
            output.append(alpha_morph(previous, following, step / (BOUNDARY_INBETWEENS + 1)))
        output.extend(native[start:start + CELLS_PER_PHASE])
    return output


def close_handoffs(frames, loop_start):
    """Add dedicated loop bridges without overwriting generated body cels."""
    output = []
    for step in range(1, HANDOFF_CELLS):
        output.append(alpha_morph(loop_start, frames[0], smoothstep(step / HANDOFF_CELLS)))
    output.extend(frame.copy() for frame in frames)
    for step in range(1, HANDOFF_CELLS + 1):
        output.append(alpha_morph(frames[-1], loop_start, smoothstep(step / HANDOFF_CELLS)))
    return output


def load_dive_frames():
    image = Image.open(DIVE)
    frames = []
    for index in range(image.n_frames):
        image.seek(index)
        frames.append(image.convert('RGBA').copy())
    if len(frames) != DIVE_FRAMES:
        raise RuntimeError(f'Expected {DIVE_FRAMES} existing dive frames, got {len(frames)}')
    return frames


def save_webp(path, frames):
    frames[0].save(
        path,
        save_all=True,
        append_images=frames[1:],
        duration=[FRAME_MS] * len(frames),
        loop=0,
        lossless=True,
        method=6,
        exact=True,
    )


def encoded_frame_count(path):
    with Image.open(path) as image:
        return image.n_frames


def body_signature(frame):
    alpha = np.asarray(frame.convert('RGBA'), dtype=np.uint8)[:, :, 3]
    moving = remove_waterline(alpha, WATER_Y)
    body = largest_component(moving, include_mask=True)
    x0, y0, x1, y1 = body['bbox']
    crop = Image.fromarray(body['mask'][y0:y1 + 1, x0:x1 + 1], 'L').resize((64, 64), Image.Resampling.NEAREST)
    signature = np.asarray(crop, dtype=np.uint8)
    left_edge = np.where(body['mask'][:, x0:min(x1 + 1, x0 + max(2, body['width'] // 5))] > 0)
    tail_y = float(np.median(left_edge[0])) if len(left_edge[0]) else float(body['cy'])
    return signature, body, tail_y


def alpha_delta(left, right):
    a = np.asarray(left.convert('RGBA'), dtype=np.int16)[:, :, 3]
    b = np.asarray(right.convert('RGBA'), dtype=np.int16)[:, :, 3]
    return float(np.abs(a - b).mean() / 255.0)


def contact_sheet(frames, path):
    cell, cols = 96, 8
    rows = math.ceil(len(frames) / cols)
    canvas = Image.new('RGB', (cols * cell, rows * cell), '#f4f6ff')
    draw = ImageDraw.Draw(canvas)
    for index, frame in enumerate(frames):
        background = Image.new('RGBA', frame.size, 'white')
        background.alpha_composite(frame)
        tile = background.convert('RGB').resize((cell - 4, cell - 4), Image.Resampling.LANCZOS)
        x, y = (index % cols) * cell + 2, (index // cols) * cell + 2
        canvas.paste(tile, (x, y))
        draw.text((x + 2, y + 2), str(index + 1), fill='#667085')
    canvas.save(path, optimize=True)


def main():
    dive = load_dive_frames()
    loop_start_alpha = np.asarray(dive[0], dtype=np.uint8)[:, :, 3]
    old_body = largest_component(remove_waterline(loop_start_alpha, WATER_Y))
    canonical_line = waterline_from(dive[0])

    raw_cells = []
    sheet_sizes = {}
    for path in PHASES:
        size, cells = crop_cells(path)
        sheet_sizes[path.name] = size
        raw_cells.extend(cells)
    if len(raw_cells) != NATIVE_CELS:
        raise RuntimeError(f'Expected {NATIVE_CELS} native Image Gen cels, got {len(raw_cells)}')

    native, normalization = normalize_native_cells(raw_cells, old_body, canonical_line)
    articulated = assemble_native_phases(native)
    spout = close_handoffs(articulated, dive[0])
    contact_sheet(spout, CONTACT)
    peak_index = CELLS_PER_PHASE + BOUNDARY_INBETWEENS + CELLS_PER_PHASE + BOUNDARY_INBETWEENS + 5

    # Product choreography: retain the accepted 60-frame dive pixel-for-pixel,
    # then play the 77-frame surface-spout act. The spout's final handoff cell
    # is exactly dive[0], so the 137-frame status loop closes without a hidden
    # third act or a timing hold.
    status = dive + spout
    if any(np.any(np.asarray(status[index]) != np.asarray(dive[index])) for index in range(DIVE_FRAMES)):
        raise RuntimeError('The original dive prefix was modified')
    save_webp(RUNTIME, status)
    spout[peak_index].save(RUNTIME_STATIC, optimize=True)

    signatures, body_metrics, tail_y = [], [], []
    for frame in spout[INBOUND_HANDOFF_FRAMES:-OUTBOUND_HANDOFF_FRAMES]:
        signature, body, tail = body_signature(frame)
        signatures.append(signature)
        body_metrics.append(body)
        tail_y.append(tail)
    shape_deltas = [float(np.abs(signatures[i].astype(np.int16) - signatures[i - 1].astype(np.int16)).mean() / 255.0) for i in range(1, len(signatures))]
    aspect = [body['width'] / body['height'] for body in body_metrics]
    body_hashes = [hashlib.sha256(signature.tobytes()).hexdigest() for signature in signatures]

    adjacent = [alpha_delta(status[i], status[(i + 1) % len(status)]) for i in range(len(status))]
    native_cels_retained = all(
        any(np.array_equal(np.asarray(native_frame), np.asarray(spout_frame)) for spout_frame in spout)
        for native_frame in native
    )
    report = {
        'method': 'four GPT Image 2 4x4 surface-spout sprite sheets; all 64 native poses retained; canonical waterline; strict 60-frame dive then 77-frame spout choreography',
        'inputs': {
            'phaseSheets': {
                path.name: {
                    'size': list(sheet_sizes[path.name]),
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                    'nativeCels': CELLS_PER_PHASE,
                }
                for path in PHASES
            },
            'nativeImageGenCels': len(raw_cells),
            'boundaryInbetweens': BOUNDARY_INBETWEENS * (len(PHASES) - 1),
            'handoffInbetweens': INBOUND_HANDOFF_FRAMES + OUTBOUND_HANDOFF_FRAMES,
        },
        'output': {
            'animation': RUNTIME.relative_to(ROOT).as_posix(),
            'static': RUNTIME_STATIC.relative_to(ROOT).as_posix(),
            'contact': CONTACT.relative_to(ROOT).as_posix(),
            'diveFramesFirst': len(dive),
            'spoutFramesSecond': len(spout),
            'statusFrames': len(status),
            'statusEncodedFrames': encoded_frame_count(RUNTIME),
            'frameMs': FRAME_MS,
            'statusDurationMs': len(status) * FRAME_MS,
            'animationBytes': RUNTIME.stat().st_size,
            'staticBytes': RUNTIME_STATIC.stat().st_size,
            'diveToSpoutDelta': adjacent[DIVE_FRAMES - 1],
            'loopSeamDelta': adjacent[-1],
            'adjacentDelta': {
                'mean': float(np.mean(adjacent)),
                'p95': float(np.percentile(adjacent, 95)),
                'max': float(max(adjacent)),
            },
            'segments': [
                {
                    'name': 'dive',
                    'source': 'assets/whale-dive.webp',
                    'statusStart': 0,
                    'statusEnd': DIVE_FRAMES - 1,
                    'sourceStart': 0,
                    'sourceEnd': len(dive) - 1,
                    'frames': len(dive),
                },
                {
                    'name': 'spout',
                    'source': 'artwork-sources/spout-imagegen-v1',
                    'statusStart': DIVE_FRAMES,
                    'statusEnd': len(status) - 1,
                    'sourceStart': 0,
                    'sourceEnd': len(spout) - 1,
                    'frames': len(spout),
                },
            ],
        },
        'nativeBodyMotion': {
            'uniqueNormalizedBodyShapes': len(set(body_hashes)),
            'shapeDeltaMean': float(np.mean(shape_deltas)),
            'shapeDeltaP95': float(np.percentile(shape_deltas, 95)),
            'aspectRatioRange': float(max(aspect) - min(aspect)),
            'tailVerticalRangePx': float(max(tail_y) - min(tail_y)),
        },
        'normalization': normalization,
        'checks': {},
    }
    checks = report['checks']
    checks['allFourSpoutImageGenSheetsPresent'] = len(sheet_sizes) == 4
    checks['all64NativeCelsUsed'] = len(raw_cells) == NATIVE_CELS
    checks['all64NativeCelsRetainedExactly'] = native_cels_retained
    checks['allSixBoundaryInbetweensPresent'] = len(articulated) == NATIVE_CELS + BOUNDARY_INBETWEENS * (len(PHASES) - 1)
    checks['allSevenHandoffInbetweensPresent'] = len(spout) == len(articulated) + INBOUND_HANDOFF_FRAMES + OUTBOUND_HANDOFF_FRAMES
    checks['oldDivePrefixPixelExact'] = all(np.array_equal(np.asarray(status[i]), np.asarray(dive[i])) for i in range(DIVE_FRAMES))
    checks['spoutSuffixPixelExact'] = all(np.array_equal(np.asarray(status[DIVE_FRAMES + i]), np.asarray(spout[i])) for i in range(len(spout)))
    checks['diveThenSpoutOnly'] = len(status) == DIVE_FRAMES + len(spout) == 137
    checks['statusEncodedFrameCountExpected'] = report['output']['statusEncodedFrames'] == len(status) == 137
    checks['uniform33msTiming'] = report['output']['statusDurationMs'] == 137 * FRAME_MS == 4521
    checks['spoutLoopClosureExact'] = np.array_equal(np.asarray(spout[-1]), np.asarray(dive[0]))
    checks['statusLastEqualsDiveFirst'] = np.array_equal(np.asarray(status[-1]), np.asarray(dive[0]))
    checks['atLeast48DistinctBodyShapes'] = report['nativeBodyMotion']['uniqueNormalizedBodyShapes'] >= 48
    checks['torsoShapeDeltaMeanAbove0_03'] = report['nativeBodyMotion']['shapeDeltaMean'] > 0.03
    checks['aspectRatioRangeAbove0_10'] = report['nativeBodyMotion']['aspectRatioRange'] > 0.10
    checks['tailVerticalRangeAbove8px'] = report['nativeBodyMotion']['tailVerticalRangePx'] > 8.0
    checks['allPassed'] = all(checks.values())
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'method': report['method'],
        'output': report['output'],
        'nativeBodyMotion': report['nativeBodyMotion'],
        'checks': checks,
    }, ensure_ascii=False, indent=2))
    if not checks['allPassed']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
