import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFile, readdir, stat } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import vm from 'node:vm'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const manifest = JSON.parse(await readFile(resolve(root, 'assets/manifest.json'), 'utf8'))
const client = await readFile(resolve(root, 'lib/client.js'), 'utf8')
const packageJson = JSON.parse(await readFile(resolve(root, 'package.json'), 'utf8'))
const expectedStates = ['dive', 'classic']
const expected = {
  dive: {
    canvas: [352, 352], frames: 60, frameDurationMs: 33, loopDurationMs: 1980,
    animatedBlob: '5c2891f6aa8a8c318a987951138178195898076e',
    staticBlob: 'a04f807b546b2ec4f4310764c2bd7c0fa29bcd56',
    commit: '65e1205d1fbf4b01997e6dfc099103b0f9717e37',
  },
  classic: {
    canvas: [184, 184], frames: 618, frameDurationMs: 17, loopDurationMs: 10506,
    animatedBlob: 'bf3d4efc4a0e38f285226722d9cf2f431b095a45',
    staticBlob: '0a697352a92f25fb8c1794e485be7fa44efe0e78',
    commit: '95b06e3f0e6ea817d25858eb29f7064a233b3c65',
  },
}

function digest(data, algorithm = 'sha256') {
  return createHash(algorithm).update(data).digest('hex')
}

function gitBlobSha(data) {
  return createHash('sha1').update(Buffer.from(`blob ${data.length}\0`)).update(data).digest('hex')
}

function webpDurations(data) {
  assert.equal(data.subarray(0, 4).toString('ascii'), 'RIFF')
  assert.equal(data.subarray(8, 12).toString('ascii'), 'WEBP')
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

assert.equal(packageJson.version, '0.7.0')
assert.deepEqual(Object.keys(manifest.states), expectedStates)
assert.deepEqual(manifest.playlist, expectedStates)
assert.equal(manifest.defaultState, 'dive')
assert.equal(manifest.playlistIntervalMs, 11000)
assert.equal(manifest.canvasScope, 'per-state')

const assetNames = (await readdir(resolve(root, 'assets'))).sort()
assert.deepEqual(assetNames, [
  'manifest.json',
  'whale-classic.png', 'whale-classic.webp',
  'whale-dive.png', 'whale-dive.webp',
  'whale-static.png',
].sort(), 'assets must contain only the two original animations and compatibility PNG')

const expectedDigests = new Set()
let totalAssetBytes = 0
for (const state of expectedStates) {
  const entry = manifest.states[state]
  const contract = expected[state]
  const animated = await readFile(resolve(root, 'assets', entry.animated))
  const reduced = await readFile(resolve(root, 'assets', entry.static))
  const durations = webpDurations(animated)
  assert.equal(entry.source, 'legacy')
  assert.deepEqual(entry.canvas, contract.canvas)
  assert.equal(entry.frames, contract.frames)
  assert.equal(entry.frameDurationMs, contract.frameDurationMs)
  assert.equal(entry.loopDurationMs, contract.loopDurationMs)
  assert.equal(entry.preservedFrom, contract.commit)
  assert.equal(gitBlobSha(animated), contract.animatedBlob, `${state}: preserved WebP bytes changed`)
  assert.equal(gitBlobSha(reduced), contract.staticBlob, `${state}: preserved PNG bytes changed`)
  assert.equal(digest(animated), entry.animatedSha256)
  assert.equal(digest(reduced), entry.staticSha256)
  assert.equal(animated.length, entry.animatedBytes)
  assert.equal(reduced.length, entry.staticBytes)
  assert.equal(durations.length, contract.frames)
  assert.ok(durations.every(value => value === contract.frameDurationMs))
  expectedDigests.add(entry.animatedSha256)
  expectedDigests.add(entry.staticSha256)
  totalAssetBytes += animated.length + reduced.length
}
assert.ok((await readFile(resolve(root, 'assets/whale-static.png'))).equals(await readFile(resolve(root, 'assets/whale-dive.png'))))

const embedded = [...client.matchAll(/data:image\/(webp|png);base64,([A-Za-z0-9+/=]+)/g)]
assert.equal(embedded.length, 4)
assert.deepEqual(new Set(embedded.map(match => digest(Buffer.from(match[2], 'base64')))), expectedDigests)
assert.ok(client.includes('@keyframes dsh-whale-switch-dive'))
assert.ok(client.includes('@keyframes dsh-whale-switch-classic'))
assert.ok(!client.includes('dsh-whale-switch-sonar'))
assert.ok(client.includes('prefers-reduced-motion: reduce'))
assert.ok(client.includes('html[data-theme=\\"dark\\"]') || client.includes('html[data-theme="dark"]'))
assert.ok(!client.includes('https://') && !client.includes('http://'))
assert.ok(client.length < 1.25 * 1024 * 1024)

let loaded
const context = {
  window: { __ModuleLoader__: { load(value) { loaded = value } } },
  console,
}
context.globalThis = context
vm.runInNewContext(client, context, { filename: 'lib/client.js' })
const plugin = loaded.factory(() => { throw new Error('No imports expected') })
assert.deepEqual([...plugin.playlist], expectedStates)
assert.equal(plugin.resolveWhaleState('Classic whale animation'), 'classic')
assert.equal(plugin.resolveWhaleState('经典鲸鱼'), 'classic')
assert.equal(plugin.resolveWhaleState('Analyzing the request'), 'dive')
assert.equal(plugin.resolveWhaleState('Searching the web'), null)
assert.equal(plugin.chooseWhaleState('Deep diving...', 0), 'dive')
assert.equal(plugin.chooseWhaleState('Deep diving...', 11000), 'classic')
assert.equal(plugin.chooseWhaleState('Deep diving...', 22000), 'dive')
assert.equal(plugin.chooseWhaleState('Deep diving...', 11000, true), 'dive')

const packedAssets = (await stat(resolve(root, 'lib/client.js'))).size
console.log(JSON.stringify({
  ok: true,
  states: expectedStates,
  playlist: manifest.playlist,
  preservedBlobChecks: 4,
  totalAssetBytes,
  clientBytes: packedAssets,
}))
