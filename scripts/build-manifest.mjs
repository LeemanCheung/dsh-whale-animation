import { createHash } from 'node:crypto'
import { readFile, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')

const profiles = {
  dive: {
    label: 'REFINED DIVE',
    summary: 'The v0.3 refined loop, retained byte-for-byte',
    canvas: [352, 352],
    frames: 60,
    frameDurationMs: 33,
    preservedFrom: '65e1205d1fbf4b01997e6dfc099103b0f9717e37',
    animatedBlob: '5c2891f6aa8a8c318a987951138178195898076e',
    staticBlob: 'a04f807b546b2ec4f4310764c2bd7c0fa29bcd56',
  },
  classic: {
    label: 'CLASSIC',
    summary: 'The first published loop, retained byte-for-byte',
    canvas: [184, 184],
    frames: 618,
    frameDurationMs: 17,
    preservedFrom: '95b06e3f0e6ea817d25858eb29f7064a233b3c65',
    animatedBlob: 'bf3d4efc4a0e38f285226722d9cf2f431b095a45',
    staticBlob: '0a697352a92f25fb8c1794e485be7fa44efe0e78',
  },
}

function sha256(data) {
  return createHash('sha256').update(data).digest('hex')
}

function gitBlobSha(data) {
  return createHash('sha1')
    .update(Buffer.from(`blob ${data.length}\0`, 'utf8'))
    .update(data)
    .digest('hex')
}

function webpDurations(data) {
  if (data.subarray(0, 4).toString('ascii') !== 'RIFF' || data.subarray(8, 12).toString('ascii') !== 'WEBP') {
    throw new Error('Animated asset is not a RIFF WebP')
  }
  const durations = []
  for (let offset = 12; offset + 8 <= data.length;) {
    const kind = data.subarray(offset, offset + 4).toString('ascii')
    const size = data.readUInt32LE(offset + 4)
    const payload = offset + 8
    if (kind === 'ANMF') durations.push(data.readUIntLE(payload + 12, 3))
    offset = payload + size + (size & 1)
  }
  return durations
}

const states = {}
for (const [state, profile] of Object.entries(profiles)) {
  const animatedName = `whale-${state}.webp`
  const staticName = `whale-${state}.png`
  const animated = await readFile(resolve(root, 'assets', animatedName))
  const reduced = await readFile(resolve(root, 'assets', staticName))
  const durations = webpDurations(animated)
  if (gitBlobSha(animated) !== profile.animatedBlob) throw new Error(`${state}: preserved WebP bytes changed`)
  if (gitBlobSha(reduced) !== profile.staticBlob) throw new Error(`${state}: preserved PNG bytes changed`)
  if (durations.length !== profile.frames || durations.some(value => value !== profile.frameDurationMs)) {
    throw new Error(`${state}: preserved timing changed`)
  }
  states[state] = {
    label: profile.label,
    summary: profile.summary,
    playlist: true,
    source: 'legacy',
    animated: animatedName,
    static: staticName,
    canvas: profile.canvas,
    frames: profile.frames,
    frameDurationMs: profile.frameDurationMs,
    loopDurationMs: durations.reduce((sum, value) => sum + value, 0),
    animatedBytes: animated.length,
    staticBytes: reduced.length,
    animatedSha256: sha256(animated),
    staticSha256: sha256(reduced),
    preservedFrom: profile.preservedFrom,
  }
}

const diveStatic = await readFile(resolve(root, 'assets', 'whale-dive.png'))
const compatibilityStatic = await readFile(resolve(root, 'assets', 'whale-static.png'))
if (!diveStatic.equals(compatibilityStatic)) throw new Error('whale-static.png must remain the Dive compatibility alias')

const manifest = {
  schemaVersion: 1,
  canvasScope: 'per-state',
  defaultState: 'dive',
  playlist: ['dive', 'classic'],
  playlistIntervalMs: 11_000,
  states,
}

await writeFile(resolve(root, 'assets', 'manifest.json'), `${JSON.stringify(manifest, null, 2)}\n`, 'utf8')
console.log(JSON.stringify({ states: Object.keys(states), playlist: manifest.playlist, preserved: true }))
