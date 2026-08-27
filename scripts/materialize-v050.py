#!/usr/bin/env python3
from __future__ import annotations
import base64, json, lzma, pathlib, shutil
ROOT=pathlib.Path(__file__).resolve().parents[1]
PARTS=ROOT/'scripts/.v050-payload'
data=''.join(path.read_text(encoding='ascii') for path in sorted(PARTS.glob('part-*.txt')))
payload=json.loads(lzma.decompress(base64.b85decode(data.encode('ascii'))).decode('utf-8'))
for item in payload['files']:
    target=ROOT/item['path']
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(item['content'],encoding='utf-8')
    target.chmod(item['mode'])
shutil.rmtree(PARTS)
pathlib.Path(__file__).unlink()
print(json.dumps({'materialized':len(payload['files'])}))
