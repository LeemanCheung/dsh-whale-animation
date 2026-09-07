"""Assemble existing ImageGen drawings; never draw a whale with code.

Extract each whole generated pose, register the source eye, and use bidirectional
optical-flow in-betweens. Native drawings appear unchanged after the documented
alpha extraction / uniform registration. Old Dive and Classic files are untouched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

# Keep offline asset work from occupying every CPU core while the user watches
# native playback. Set before either OpenCV or NumPy imports a BLAS runtime.
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'artwork-sources/four-actions'
OUT = ROOT / '.artifacts/four-actions'
SIZE = 352
SCALE = 0.62
STATES = {
    'scout': {'label': 'SCOUT', 'summary': 'Curious bubble tracking with a curling torso', 'frames': 144, 'eyeY': 108},
    'surge': {'label': 'SURGE', 'summary': 'A traveling body flex and tail-powered swim', 'frames': 120, 'eyeY': 150},
    'flow': {'label': 'FLOW', 'summary': 'A compact C-shaped torso softly coils and relaxes', 'frames': 180, 'eyeY': 124},
    'breathe': {'label': 'BREATHE', 'summary': 'Rise, arch, exhale and settle', 'frames': 216, 'eyeY': 155},
}
cv2.setNumThreads(1)
cv2.setUseOptimized(False)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def drawings(rgb):
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    count, labels, stats, centers = cv2.connectedComponentsWithStats((gray < 110).astype('uint8'), 8)
    big = [i for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] > 2400]
    if len(big) != 8:
        raise ValueError(f'Expected 8 complete generated whales, found {len(big)}')
    big.sort(key=lambda i: centers[i, 1])
    ordered = [i for row in range(2) for i in sorted(big[row*4:row*4+4], key=lambda i: centers[i, 0])]
    groups = {i: [i] for i in ordered}
    for i in range(1, count):
        if i in big or stats[i, cv2.CC_STAT_AREA] < 3:
            continue
        nearest = min(big, key=lambda j: np.linalg.norm(centers[i]-centers[j]))
        if np.linalg.norm(centers[i]-centers[nearest]) < 230:
            groups[nearest].append(i)
    return gray, labels, stats, ordered, groups


def find_eye(gray, body_box):
    bx, by, bw, bh = body_box
    head = gray[by:by+bh, bx:bx+bw]
    count, _, stats, centers = cv2.connectedComponentsWithStats((head > 195).astype('uint8'), 8)
    candidates = []
    for i in range(1, count):
        x, y, w, h, area = stats[i]
        if (4 <= area <= 160 and .4 <= w/h <= 2.0 and x > bw*.55
                and y < bh*.94 and x > 0 and y > 0 and x+w < bw and y+h < bh):
            candidates.append((area, centers[i]+[bx, by]))
    if not candidates:
        raise ValueError(f'No enclosed generated eye in {body_box}')
    return max(candidates, key=lambda item: item[0])[1]


def extract(state):
    source_path = SOURCE / f'{state}.png'
    rgb = np.asarray(Image.open(source_path).convert('RGB'))
    if state == 'flow': rgb = cv2.medianBlur(rgb, 3)
    gray, labels, stats, ordered, groups = drawings(rgb)
    poses = []
    records = []
    # One global scale per sheet keeps head size honest; no per-pose stretching.
    scale = SCALE * (1536 / rgb.shape[1])
    for index, component in enumerate(ordered):
        x, y, w, h, _ = stats[component]
        eye = find_eye(gray, (x, y, w, h))
        selected = np.isin(labels, groups[component]).astype('uint8')
        selected = cv2.dilate(selected, np.ones((5, 5), dtype='uint8'))
        # The asset is monochrome ink. White belly and eye become deliberate
        # negative space; no synthetic outline or new anatomy is introduced.
        # Solid monochrome ink: remove low-amplitude paper/grain modulation
        # inside the dark source paint; preserve antialiasing at its edge.
        alpha = np.clip((230-gray.astype('float32'))*255/70, 0, 255) * selected
        offset_y = STATES[state]['eyeY'] - eye[1]*scale
        water = []
        if state == 'breathe':
            water = [i for i in groups[component] if stats[i, 2] > 16
                     and stats[i, 3] < 14 and stats[i, 1] > eye[1]]
            if not water:
                raise ValueError(f'Breathe pose {index+1} has no generated water ripple')
            baseline = max(stats[i, 1]+stats[i, 3]/2 for i in water)
            offset_y = 238-baseline*scale
        matrix = np.array([[scale, 0, 268-eye[0]*scale], [0, scale, offset_y]], dtype='float32')
        normalized = cv2.warpAffine(alpha, matrix, (SIZE, SIZE), flags=cv2.INTER_CUBIC)
        normalized = np.clip(normalized, 0, 255).round().astype('uint8')
        poses.append(normalized)
        records.append({'pose': index+1, 'bodyBox': [int(x), int(y), int(w), int(h)],
                        'sourceEye': eye.round(4).tolist(), 'scale': round(scale, 8),
                        'offset': matrix[:, 2].round(4).tolist(),
                        'sourceComponents': [int(i) for i in groups[component]],
                        'registeredAlphaSha256': digest(normalized.tobytes())})
    return poses, records




def signed_distance(alpha):
    binary = (alpha > 127).astype('uint8')
    return cv2.distanceTransform(binary, cv2.DIST_L2, 5)-cv2.distanceTransform(1-binary, cv2.DIST_L2, 5)




def inbetweens(poses, index, steps):
    first, second = poses[index], poses[(index+1) % len(poses)]
    estimator = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)
    forward = estimator.calc(first, second, None)
    backward = estimator.calc(second, first, None)
    yy, xx = np.mgrid[0:SIZE, 0:SIZE].astype('float32')
    grid = np.dstack([xx, yy])
    yield first
    for step in range(1, steps):
        t = step/steps
        maps = []
        for flow, factor in [(forward,t),(backward,1-t)]:
            mapping = grid.copy()
            for _ in range(3):
                sampled = cv2.remap(flow,mapping[:,:,0],mapping[:,:,1],cv2.INTER_LINEAR)
                mapping = grid-factor*sampled
            maps.append(mapping)
        a = cv2.remap(first,maps[0][:,:,0],maps[0][:,:,1],cv2.INTER_CUBIC).astype('float32')
        b = cv2.remap(second,maps[1][:,:,0],maps[1][:,:,1],cv2.INTER_CUBIC).astype('float32')
        yield np.clip(a*(1-t)+b*t,0,255).round().astype('uint8')


def rgba(alpha):
    pixels = np.zeros((SIZE, SIZE, 4), dtype='uint8')
    pixels[:, :, 3] = alpha
    return Image.fromarray(pixels)


def measurements(frames, poses):
    border = min(min(np.where(frame > 0)[0].min(), SIZE-1-np.where(frame > 0)[0].max(),
                     np.where(frame > 0)[1].min(), SIZE-1-np.where(frame > 0)[1].max()) for frame in frames)
    deltas = [float(np.abs(frames[(i+1) % len(frames)].astype('float32')-frame).mean())
              for i, frame in enumerate(frames)]
    middle = [pose[50:315, 150:225].astype('float32') for pose in poses]
    torso_deltas = [float(np.abs(middle[(i+1) % len(middle)]-part).mean()) for i, part in enumerate(middle)]
    return {'uniqueFrames': len({digest(x.tobytes()) for x in frames}),
            'minimumAdjacentAlphaDelta': round(min(deltas), 6),
            'transparentMarginPx': int(border), 'maximumAdjacentAlphaDelta': round(max(deltas), 6),
            'loopSeamAlphaDelta': round(deltas[-1], 6),
            'registeredTorsoMaximumDelta': round(max(torso_deltas), 6)}


def build(state, publish=False, check=False):
    directory = OUT / state
    directory.mkdir(parents=True, exist_ok=True)
    poses, records = extract(state)
    config = STATES[state]
    order = list(range(8))+list(range(6,0,-1)) if state == 'scout' else list(range(8))
    playback_poses = [poses[i] for i in order]
    anchors = [round(i*config['frames']/len(order)) for i in range(len(order)+1)]
    frames = [frame for i in range(len(order))
              for frame in inbetweens(playback_poses, i, anchors[i+1]-anchors[i])]
    timing = [round((i+1)*1000/60)-round(i*1000/60) for i in range(len(frames))]
    images = [rgba(frame) for frame in frames]
    stats = measurements(frames, poses)
    if stats['transparentMarginPx'] < 4:
        raise ValueError(f'{state}: cropped or nearly cropped frame: {stats}')
    required_unique = len(frames)//2 if state == 'scout' else len(frames)
    if stats['uniqueFrames'] < required_unique or stats['minimumAdjacentAlphaDelta'] == 0:
        raise ValueError(f'{state}: duplicate playback frames: {stats}')
    if stats['registeredTorsoMaximumDelta'] < 3:
        raise ValueError(f'{state}: insufficient generated torso articulation: {stats}')
    motion_path = directory / f'whale-{state}.webp'
    images[0].save(motion_path, save_all=True, append_images=images[1:], duration=timing,
                   loop=0, lossless=True, method=6, exact=True)
    poster_index = {'scout': 3, 'surge': 0, 'flow': 4, 'breathe': 4}[state]
    still_path = directory / f'whale-{state}.png'
    rgba(poses[poster_index]).save(still_path)
    board = Image.new('RGB', (4*176, 2*198), '#eef2f5')
    draw = ImageDraw.Draw(board)
    for i, pose in enumerate(poses):
        thumb = Image.new('RGBA', (SIZE, SIZE), 'white')
        thumb.alpha_composite(rgba(pose))
        board.paste(thumb.convert('RGB').resize((176, 176), Image.Resampling.LANCZOS), (i % 4*176, i//4*198+22))
        draw.text((i % 4*176+10, i//4*198+5), f'{state} {i+1:02}', fill='#293644')
    board.save(directory / 'contact.png')
    transitions = Image.new('RGB', (6*132,4*154), '#eef2f5')
    transition_labels = ImageDraw.Draw(transitions)
    for sample in range(24):
        frame_number = round(sample*len(images)/24) % len(images)
        thumb = Image.new('RGBA', (SIZE,SIZE), 'white')
        thumb.alpha_composite(images[frame_number])
        transitions.paste(thumb.convert('RGB').resize((132,132), Image.Resampling.LANCZOS), (sample%6*132, sample//6*154+22))
        transition_labels.text((sample%6*132+7,sample//6*154+5), f'{frame_number:03}', fill='#293644')
    transitions.save(directory/'transitions.png')
    report = {'state': state, 'label': config['label'], 'summary': config['summary'],
              'source': f'artwork-sources/four-actions/{state}.png',
              'sourceSha256': digest((SOURCE / f'{state}.png').read_bytes()),
              'identitySha256': digest((SOURCE / 'identity.png').read_bytes()),
              'canvas': [SIZE, SIZE], 'generatedDrawings': len(poses), 'nativeFrameIndices': anchors[:-1],
              'nativePoseOrder': [i+1 for i in order], 'nativeFrames': len(order),
              'returnTrip': state == 'scout',
              'interpolatedFrames': len(frames)-len(order), 'frames': len(frames), 'fps': 60,
              'durationsMs': timing, 'loopDurationMs': sum(timing),
              'posterPose': poster_index+1, 'nativePoseRecords': records, 'metrics': stats,
              'method': 'uniform source-eye registration; restrained generated pose family; bidirectional DIS raster in-betweens',
              'animatedSha256': digest(motion_path.read_bytes()), 'staticSha256': digest(still_path.read_bytes())}
    (directory / 'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    if publish:
        (ROOT / 'assets' / motion_path.name).write_bytes(motion_path.read_bytes())
        (ROOT / 'assets' / still_path.name).write_bytes(still_path.read_bytes())
        (ROOT / 'artwork-sources/four-actions' / f'{state}-report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
        (ROOT / 'docs/four-actions').mkdir(parents=True, exist_ok=True)
        (ROOT / 'docs/four-actions' / f'{state}-contact.png').write_bytes((directory / 'contact.png').read_bytes())
    if check:
        recorded = json.loads((SOURCE / f'{state}-report.json').read_text(encoding='utf-8'))
        for name, field in [(motion_path.name, 'animatedSha256'), (still_path.name, 'staticSha256')]:
            if digest((ROOT / 'assets' / name).read_bytes()) != recorded[field]:
                raise ValueError(f'{state}: published file hash changed')
        for field in ['sourceSha256', 'identitySha256', 'canvas', 'frames', 'generatedDrawings', 'durationsMs', 'posterPose', 'nativeFrameIndices', 'nativePoseOrder']:
            if report[field] != recorded[field]:
                raise ValueError(f'{state}: {field} contract changed')
        with Image.open(ROOT / 'assets' / motion_path.name) as encoded:
            if encoded.n_frames != len(frames):
                raise ValueError(f'{state}: encoded frame count changed')
            for i, frame in enumerate(frames):
                encoded.seek(i)
                decoded = np.asarray(encoded.convert('RGBA'))[:, :, 3]
                error = np.abs(decoded.astype('int16')-frame.astype('int16'))
                if error.max() > 1:
                    raise ValueError(f'{state}: rebuilt frame {i+1} differs by {error.max()} levels')
                if i in anchors[:-1]:
                    native = poses[order[anchors.index(i)]]
                    if not np.array_equal(frame,native):
                        raise ValueError(f'{state}: original generated pose omitted at {i}')
        with Image.open(ROOT / 'assets' / still_path.name) as still:
            if not np.array_equal(np.asarray(still.convert('RGBA')),np.asarray(rgba(poses[poster_index]))):
                raise ValueError(f'{state}: static fallback differs from selected generated pose')
    print(json.dumps({'state': state, 'frames': len(frames), 'durationMs': sum(timing), 'metrics': stats, 'check': check}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', choices=STATES)
    parser.add_argument('--publish', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for selected in ([args.state] if args.state else STATES):
        build(selected, publish=args.publish, check=args.check)
