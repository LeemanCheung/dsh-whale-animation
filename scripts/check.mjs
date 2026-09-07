import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFile, readdir, stat } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import vm from 'node:vm'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const manifest = JSON.parse(await readFile(resolve(root, 'assets/manifest.json'), 'utf8'))
const client = await readFile(resolve(root, 'lib/client.js'), 'utf8')
assert.ok(!client.includes('\r'), 'client bundle must use canonical LF on Windows and Linux')
const packageJson = JSON.parse(await readFile(resolve(root, 'package.json'), 'utf8'))
const expectedStates = ['dive', 'classic', 'scout', 'surge', 'flow', 'breathe']
const newFrames = { scout: 144, surge: 120, flow: 180, breathe: 216 }
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

assert.equal(packageJson.version, '0.8.0')
assert.ok(!packageJson.peerDependencies['@deepseek-ai/dsh-client-runtime'])
assert.ok(!(packageJson.dsh.client.inject ?? []).includes('@deepseek-ai/dsh-client-runtime'))
assert.deepEqual(Object.keys(manifest.states), expectedStates)
assert.deepEqual(manifest.playlist, expectedStates)
assert.equal(manifest.defaultState, 'dive')
assert.equal(manifest.playlistCycleDurationMs, 23486)
assert.equal(manifest.canvasScope, 'per-state')

const assetNames = (await readdir(resolve(root, 'assets'))).sort()
assert.deepEqual(assetNames, [
  'manifest.json',
  'whale-classic.png', 'whale-classic.webp',
  'whale-dive.png', 'whale-dive.webp',
  'whale-static.png',
  ...Object.keys(newFrames).flatMap(state => [`whale-${state}.png`, `whale-${state}.webp`]),
].sort(), 'assets must contain exactly two preserved loops and four new actions')

const expectedDigests = new Set()
let totalAssetBytes = 0
for (const state of ['dive', 'classic']) {
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
for (const [state, frames] of Object.entries(newFrames)) {
  const entry = manifest.states[state]
  const animated = await readFile(resolve(root, 'assets', entry.animated))
  const reduced = await readFile(resolve(root, 'assets', entry.static))
  const report = JSON.parse(await readFile(resolve(root, `artwork-sources/four-actions/${state}-report.json`), 'utf8'))
  const durations = webpDurations(animated)
  assert.equal(entry.source, 'imagegen-raster')
  assert.deepEqual(entry.canvas, [352,352])
  assert.equal(frames, entry.frames)
  assert.equal(durations.length, frames)
  assert.equal(entry.fps, 60)
  assert.equal(entry.generatedDrawings, 8)
  assert.equal(entry.nativeFrames, state === 'scout' ? 14 : 8)
  assert.equal(entry.interpolatedFrames, frames-entry.nativeFrames)
  assert.equal(durations.reduce((a,b) => a+b, 0), entry.loopDurationMs)
  assert.ok(durations.every(value => value === 16 || value === 17))
  assert.equal(digest(animated), entry.animatedSha256)
  assert.equal(digest(reduced), entry.staticSha256)
  assert.equal(report.animatedSha256, entry.animatedSha256)
  assert.equal(report.staticSha256, entry.staticSha256)
  assert.equal(report.nativePoseRecords.length, 8)
  assert.equal(new Set(report.nativePoseRecords.map(item => item.pose)).size, 8)
  assert.ok(report.metrics.uniqueFrames >= (state === 'scout' ? frames/2 : frames))
  assert.ok(report.metrics.minimumAdjacentAlphaDelta > 0, 'no duplicate adjacent frames')
  assert.ok(report.metrics.transparentMarginPx >= 4)
  assert.equal(digest(await readFile(resolve(root, `artwork-sources/four-actions/${state}.png`))), report.sourceSha256)
  assert.equal(digest(await readFile(resolve(root, 'artwork-sources/four-actions/identity.png'))), report.identitySha256)
  expectedDigests.add(entry.animatedSha256)
  expectedDigests.add(entry.staticSha256)
  totalAssetBytes += animated.length+reduced.length
}
assert.ok((await readFile(resolve(root, 'assets/whale-static.png'))).equals(await readFile(resolve(root, 'assets/whale-dive.png'))))

const embedded = [...client.matchAll(/data:image\/(webp|png);base64,([A-Za-z0-9+/=]+)/g)]
assert.equal(embedded.length, 12)
assert.deepEqual(new Set(embedded.map(match => digest(Buffer.from(match[2], 'base64')))), expectedDigests)
assert.ok(client.includes('@keyframes dsh-whale-switch-dive'))
assert.ok(client.includes('@keyframes dsh-whale-switch-classic'))
assert.ok(!client.includes('dsh-whale-switch-sonar'))
for (const state of Object.keys(newFrames)) assert.ok(client.includes(`dsh-whale-switch-${state}`))
assert.ok(client.includes('prefers-reduced-motion: reduce'))
assert.ok(client.includes('html[data-theme=\\"dark\\"]') || client.includes('html[data-theme="dark"]'))
assert.ok(!client.includes('https://') && !client.includes('http://'))
assert.ok(client.length < 6 * 1024 * 1024, 'six-state bundle must stay below 6 MiB')

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
assert.equal(plugin.resolveWhaleState('Searching the web'), 'scout')
assert.equal(plugin.resolveWhaleState('Running tests'), 'surge')
assert.equal(plugin.resolveWhaleState('Writing a response'), 'flow')
assert.equal(plugin.resolveWhaleState('Waiting for a tool'), 'breathe')
assert.equal(plugin.resolveWhaleState('探泡'), 'scout')
assert.equal(plugin.resolveWhaleState('疾游'), 'surge')
assert.equal(plugin.resolveWhaleState('回旋'), 'flow')
assert.equal(plugin.resolveWhaleState('吐息'), 'breathe')
assert.equal(plugin.chooseWhaleState('Deep diving...', 0), 'dive')
assert.equal(plugin.chooseWhaleState('Deep diving...', 1979), 'dive')
assert.equal(plugin.chooseWhaleState('Deep diving...', 1980), 'classic')
assert.equal(plugin.chooseWhaleState('Deep diving...', 12485), 'classic')
assert.equal(plugin.chooseWhaleState('Deep diving...', 12486), 'scout')
assert.equal(plugin.chooseWhaleState('Deep diving...', 14886), 'surge')
assert.equal(plugin.chooseWhaleState('Deep diving...', 16886), 'flow')
assert.equal(plugin.chooseWhaleState('Deep diving...', 19886), 'breathe')
assert.equal(plugin.chooseWhaleState('Deep diving...', 23486), 'dive')
assert.equal(plugin.chooseWhaleState('Deep diving...', 11000, true), 'dive')

// A hidden DSH tab should not poll the full document. Resuming it must mount
// existing status text immediately, and hot reload must dispose every listener.
const attributes = new Map()
const properties = new Map()
const host = {
  textContent: 'Deep diving...', isConnected: true,
  style: { setProperty: (name, value) => properties.set(name, value), removeProperty: name => properties.delete(name) },
  getAttribute: name => attributes.get(name),
  setAttribute: (name, value) => attributes.set(name, value),
  removeAttribute: name => attributes.delete(name),
}
const listeners = new Map()
let timerCount = 0
let clearedTimers = 0
let removedStyles = 0
let disconnectedObservers = 0
let clockNow = 0
let timeoutCallback
let timeoutDelay
let createdImageUrls = 0
const revokedImageUrls = new Set()
context.Date = { now: () => clockNow }
context.URL = {
  createObjectURL: () => `blob:whale-${++createdImageUrls}`,
  revokeObjectURL: url => revokedImageUrls.add(url),
}
context.Blob = Blob
context.atob = value => Buffer.from(value, 'base64').toString('binary')
context.document = {
  hidden: true,
  documentElement: {},
  head: { appendChild() {} },
  createElement: () => ({ dataset: {}, remove() { removedStyles += 1 } }),
  querySelector: () => null,
  querySelectorAll: selector => selector === plugin.statusSelector ? [host] : [],
  addEventListener: (name, callback) => listeners.set(name, callback),
  removeEventListener: name => listeners.delete(name),
}
context.setTimeout = (callback, delay) => { timeoutCallback = callback; timeoutDelay = delay; return ++timerCount }
context.clearTimeout = () => { clearedTimers += 1 }
context.MutationObserver = class { observe() {} disconnect() { disconnectedObservers += 1 } }
let dispose
plugin.apply({ effect(start) { dispose = start() } })
assert.equal(timerCount, 0)
assert.equal(attributes.size, 0)
context.document.hidden = false
listeners.get('visibilitychange')()
assert.equal(timerCount, 1)
assert.equal(timeoutDelay, 1980)
assert.equal(attributes.get('data-dsh-whale-state'), 'dive')
assert.equal(properties.get('--dsh-whale-current-image'), 'url("blob:whale-1")')
clockNow = 1980
timeoutCallback()
assert.equal(attributes.get('data-dsh-whale-state'), 'classic')
assert.equal(properties.get('--dsh-whale-current-image'), 'url("blob:whale-2")')
assert.ok(revokedImageUrls.has('blob:whale-1'))
assert.equal(timeoutDelay, 10506)
host.textContent = 'Analyzing the request'
clockNow = 4000
timeoutCallback()
assert.equal(attributes.get('data-dsh-whale-state'), 'classic', 'status changes must wait until the current loop finishes')
assert.equal(timeoutDelay, 8486)
clockNow = 12486
timeoutCallback()
assert.equal(attributes.get('data-dsh-whale-state'), 'dive')
clockNow = 14499
timeoutCallback()
assert.equal(timeoutDelay, 1947, 'late repeat callbacks must keep the existing decoder clock')
context.document.hidden = true
listeners.get('visibilitychange')()
assert.equal(clearedTimers, timerCount)
assert.equal(properties.size, 0)
clockNow = 50000
context.document.hidden = false
listeners.get('visibilitychange')()
assert.equal(attributes.get('data-dsh-whale-state'), 'dive', 'visibility resume restarts the same complete loop')
assert.equal(timeoutDelay, 1980)
dispose()
assert.equal(listeners.size, 0)
assert.equal(attributes.size, 0)
assert.equal(properties.size, 0)
assert.equal(revokedImageUrls.size, createdImageUrls)
assert.equal(removedStyles, 1)
assert.equal(disconnectedObservers, 1)

context.Blob = class { constructor() { throw new Error('simulated unavailable decoder') } }
host.textContent = 'Running tests'
plugin.apply({ effect(start) { dispose = start() } })
assert.equal(attributes.get('data-dsh-whale-state'), 'surge')
assert.equal(attributes.get('data-dsh-whale-fallback'), 'true')
assert.equal(host.textContent, 'Running tests')
dispose()
assert.equal(attributes.size, 0)
assert.equal(properties.size, 0)

const packedAssets = (await stat(resolve(root, 'lib/client.js'))).size
console.log(JSON.stringify({
  ok: true,
  states: expectedStates,
  playlist: manifest.playlist,
  preservedBlobChecks: 4,
  totalAssetBytes,
  clientBytes: packedAssets,
}))
