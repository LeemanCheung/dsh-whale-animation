import json
import re
import struct
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / 'docs' / 'hero.png'
PREVIEW = ROOT / 'docs' / 'preview.webp'
READMES = [ROOT / 'README.md', ROOT / 'README.zh-CN.md']


def webp_animation(path):
    data = path.read_bytes()
    if data[:4] != b'RIFF' or data[8:12] != b'WEBP':
        raise RuntimeError(f'Not a WebP RIFF file: {path}')
    offset = 12
    durations = []
    while offset + 8 <= len(data):
        kind = data[offset:offset + 4]
        size = struct.unpack_from('<I', data, offset + 4)[0]
        payload = offset + 8
        if kind == b'ANMF':
            if size < 16:
                raise RuntimeError(f'Invalid ANMF chunk in {path}')
            durations.append(int.from_bytes(data[payload + 12:payload + 15], 'little'))
        offset = payload + size + (size & 1)
    return durations


def local_references(path):
    text = path.read_text(encoding='utf-8')
    refs = re.findall(r'(?:src="|\]\()([^"\)]+)', text)
    local = [ref.split('#', 1)[0] for ref in refs if not ref.startswith(('http://', 'https://', '#'))]
    return text, local


def main():
    hero = Image.open(HERO)
    preview = Image.open(PREVIEW)
    durations = webp_animation(PREVIEW)
    readmes = {}
    for path in READMES:
        text, refs = local_references(path)
        missing = [ref for ref in refs if not (ROOT / ref).exists()]
        if missing:
            raise RuntimeError(f'{path.name} has missing local references: {missing}')
        if text.count('```mermaid') != 1:
            raise RuntimeError(f'{path.name} must contain exactly one Mermaid diagram')
        readmes[path.name] = {'localReferences': refs, 'missing': missing}
    checks = {
        'heroSize': hero.size == (1200, 380),
        'previewSize': preview.size == (1000, 320),
        'previewDecodesAnimated': getattr(preview, 'n_frames', 1) >= 300,
        'previewRiffFramesInExpectedRange': 300 <= len(durations) <= 309,
        'previewDurationMatchesSource': sum(durations) == 618 * 17,
        'previewUnder800KiB': PREVIEW.stat().st_size < 800 * 1024,
        'readmeLinksResolve': all(not value['missing'] for value in readmes.values()),
    }
    report = {
        'hero': {'size': hero.size, 'bytes': HERO.stat().st_size},
        'preview': {
            'size': preview.size,
            'decodedFrames': getattr(preview, 'n_frames', 1),
            'riffFrames': len(durations),
            'durations': sorted(set(durations)),
            'totalMs': sum(durations),
            'bytes': PREVIEW.stat().st_size,
        },
        'readmes': readmes,
        'checks': checks,
        'ok': all(checks.values()),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['ok']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
