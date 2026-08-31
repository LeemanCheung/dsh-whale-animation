import { createHash } from 'node:crypto'
import { readFile, stat } from 'node:fs/promises'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import vm from 'node:vm'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const source = await readFile(resolve(root, 'lib/client.js'), 'utf8')
const manifest = JSON.parse(await readFile(resolve(root, 'assets/manifest.json'), 'utf8'))
const stateKeys = Object.keys(manifest.states)
const expectedStates = ['dive', 'classic', 'sonar', 'work', 'compose', 'idle', 'alert']
const expectedPlaylist = ['dive', 'classic', 'sonar', 'work', 'compose', 'idle']
const expectedDerivedFrom = {
  work: ['whale-dive.webp'],
  compose: ['whale-classic.webp'],
  idle: ['whale-dive.webp'],
  alert: ['whale-classic.webp'],
}
const allowPlaceholderLegacy = process.env.DSH_ALLOW_PLACEHOLDER_LEGACY === '1'
const expectedLegacyGitBlobs = {
  dive: {
    animated: '5c2891f6aa8a8c318a987951138178195898076e',
    static: 'a04f807b546b2ec4f4310764c2bd7c0fa29bcd56',
    commit: '65e1205d1fbf4b01997e6dfc099103b0f9717e37',
    canvas: [352, 352],
  },
  classic: {
    animated: 'bf3d4efc4a0e38f285226722d9cf2f431b095a45',
    static: '0a697352a92f25fb8c1794e485be7fa44efe0e78',
    commit: '95b06e3f0e6ea817d25858eb29f7064a233b3c65',
    canvas: [184, 184],
  },
}

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function digest(data) {
  return createHash('sha256').update(data).digest('hex')
}

function gitBlobSha(data) {
  return createHash('sha1')
    .update(Buffer.from(`blob ${data.length}\0`, 'utf8'))
    .update(data)
    .digest('hex')
}

function webpDurations(data) {
  assert(data.subarray(0, 4).toString('ascii') === 'RIFF', 'Animated asset is not RIFF')
  assert(data.subarray(8, 12).toString('ascii') === 'WEBP', 'Animated asset is not WebP')
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

assert(JSON.stringify(stateKeys) === JSON.stringify(expectedStates), `Unexpected state order: ${stateKeys}`)
assert(JSON.stringify(manifest.playlist) === JSON.stringify(expectedPlaylist), `Unexpected playlist: ${manifest.playlist}`)
assert(manifest.canvasScope === 'generated-states', 'Top-level canvas scope is ambiguous')
assert(manifest.defaultState === 'dive', 'The refined legacy dive must remain the default state')
assert(manifest.playlistIntervalMs === 11000, 'Playlist interval changed unexpectedly')
for (const state of manifest.playlist) {
  assert(
    manifest.playlistIntervalMs >= manifest.states[state].loopDurationMs,
    `${state}: playlist interval truncates the animation before one full loop`,
  )
}

let totalAnimatedBytes = 0
let totalStaticBytes = 0
const expectedAssetDigests = new Set()
const generatedAnimatedDigests = new Set()
const generatedStaticDigests = new Set()
const expectedDataUrls = new Map()
for (const state of stateKeys) {
  const entry = manifest.states[state]
  assert(entry.animated === `whale-${state}.webp`, `${state}: animated filename is mapped to another state`)
  assert(entry.static === `whale-${state}.png`, `${state}: static filename is mapped to another state`)
  const animatedPath = resolve(root, 'assets', entry.animated)
  const staticPath = resolve(root, 'assets', entry.static)
  const [animated, reduced, animatedStat, staticStat] = await Promise.all([
    readFile(animatedPath),
    readFile(staticPath),
    stat(animatedPath),
    stat(staticPath),
  ])
  const durations = webpDurations(animated)
  assert(Array.isArray(entry.canvas) && entry.canvas.length === 2, `${state}: native canvas metadata is missing`)
  assert(durations.length === entry.frames, `${state}: frames=${durations.length}, expected=${entry.frames}`)
  assert(durations.every(value => value === entry.frameDurationMs), `${state}: unexpected frame durations ${[...new Set(durations)]}`)
  assert(durations.reduce((sum, value) => sum + value, 0) === entry.loopDurationMs, `${state}: loop duration mismatch`)
  assert(animatedStat.size === entry.animatedBytes, `${state}: animated size does not match manifest`)
  assert(staticStat.size === entry.staticBytes, `${state}: static size does not match manifest`)
  assert(digest(animated) === entry.animatedSha256, `${state}: animated SHA-256 mismatch`)
  assert(digest(reduced) === entry.staticSha256, `${state}: static SHA-256 mismatch`)
  assert(reduced.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])), `${state}: reduced-motion asset is not PNG`)
  assert(animatedStat.size >= 1000 && animatedStat.size <= 1024 * 1024, `${state}: animated asset outside size budget`)
  assert(staticStat.size >= 500 && staticStat.size <= 64 * 1024, `${state}: static asset outside size budget`)

  if (expectedLegacyGitBlobs[state]) {
    const expected = expectedLegacyGitBlobs[state]
    assert(entry.source === 'legacy', `${state}: preserved asset is not marked legacy`)
    assert(entry.preservedFrom === expected.commit, `${state}: preserved source commit changed`)
    assert(JSON.stringify(entry.canvas) === JSON.stringify(expected.canvas), `${state}: preserved native canvas changed`)
    if (!allowPlaceholderLegacy) {
      assert(gitBlobSha(animated) === expected.animated, `${state}: legacy animation bytes changed`)
      assert(gitBlobSha(reduced) === expected.static, `${state}: legacy reduced-motion bytes changed`)
    }
  } else {
    assert(entry.source === 'generated', `${state}: redrawn state is not marked generated`)
    assert(JSON.stringify(entry.canvas) === JSON.stringify([352, 352]), `${state}: generated canvas changed`)
    assert(entry.frames === 48, `${state}: generated frame count changed`)
    assert(entry.frameDurationMs === 40, `${state}: generated frame cadence changed`)
    assert(entry.loopDurationMs === 1920, `${state}: generated loop duration changed`)
    assert(animatedStat.size <= 512 * 1024, `${state}: generated state exceeds 512 KiB`)
    if (expectedDerivedFrom[state]) {
      assert(JSON.stringify(entry.derivedFrom) === JSON.stringify(expectedDerivedFrom[state]), `${state}: legacy identity lineage changed`)
    } else {
      assert(entry.derivedFrom === undefined, `${state}: unexpected legacy identity lineage`)
    }
  }

  totalAnimatedBytes += animatedStat.size
  totalStaticBytes += staticStat.size
  expectedAssetDigests.add(entry.animatedSha256)
  expectedAssetDigests.add(entry.staticSha256)
  expectedDataUrls.set(state, {
    animated: `data:image/webp;base64,${animated.toString('base64')}`,
    static: `data:image/png;base64,${reduced.toString('base64')}`,
  })
  if (entry.source === 'generated') {
    generatedAnimatedDigests.add(entry.animatedSha256)
    generatedStaticDigests.add(entry.staticSha256)
  }
}
const generatedStateCount = stateKeys.filter(state => manifest.states[state].source === 'generated').length
assert(generatedAnimatedDigests.size === generatedStateCount, 'Generated states reuse the same animation')
assert(generatedStaticDigests.size === generatedStateCount, 'Generated states reuse the same reduced-motion image')
assert(totalAnimatedBytes <= 2304 * 1024, `Animated asset budget exceeded: ${totalAnimatedBytes}`)
assert(totalStaticBytes <= 160 * 1024, `Static asset budget exceeded: ${totalStaticBytes}`)

const embedded = [...source.matchAll(/data:image\/(webp|png);base64,([A-Za-z0-9+/=]+)/g)]
assert(embedded.length === stateKeys.length * 2, `Embedded data URL count mismatch: ${embedded.length}`)
const embeddedDigests = new Set(embedded.map(match => digest(Buffer.from(match[2], 'base64'))))
assert(embeddedDigests.size === expectedAssetDigests.size, 'Embedded asset digest set has duplicates or omissions')
for (const expected of expectedAssetDigests) assert(embeddedDigests.has(expected), `Embedded asset missing: ${expected}`)
assert(!source.includes('https://') && !source.includes('http://'), 'Client contains a runtime network URL')
assert(source.includes('[class*="_turnStatus"][role="status"]'), 'Semantic turn-status fallback is missing')
assert(source.includes('prefers-reduced-motion: reduce'), 'Reduced-motion CSS is missing')
assert(source.includes('html[data-theme=\\"dark\\"]') || source.includes('html[data-theme="dark"]'), 'Explicit dark-theme CSS is missing')
assert(source.includes('@keyframes dsh-whale-switch-dive'), 'Per-state switch animation is missing')
assert(source.length <= 3.5 * 1024 * 1024, `Client bundle exceeds 3.5 MiB: ${source.length}`)

class FakeElement {
  constructor(tagName, text = '') {
    this.tagName = tagName.toUpperCase()
    this._text = text
    this.attributes = new Map()
    this.children = []
    this.dataset = {}
    this.parentElement = null
    this.isConnected = true
    this.removed = false
  }

  get textContent() { return this._text }
  set textContent(value) { this._text = String(value) }
  setAttribute(name, value) { this.attributes.set(name, String(value)) }
  getAttribute(name) { return this.attributes.has(name) ? this.attributes.get(name) : null }
  removeAttribute(name) { this.attributes.delete(name) }
  appendChild(child) {
    child.parentElement = this
    child.isConnected = true
    this.children.push(child)
    return child
  }
  remove() {
    this.removed = true
    this.isConnected = false
    if (this.parentElement) {
      this.parentElement.children = this.parentElement.children.filter(child => child !== this)
      this.parentElement = null
    }
  }
}

let loaded
let now = 1_000
let intervalCallback
let intervalCleared = false
let observerDisconnected = false
let motionListener
const motionQuery = {
  matches: false,
  addEventListener(type, callback) { if (type === 'change') motionListener = callback },
  removeEventListener(type, callback) { if (type === 'change' && motionListener === callback) motionListener = undefined },
}
const status = new FakeElement('div', 'Deep diving...')
status.setAttribute('role', 'status')
const head = new FakeElement('head')
const document = {
  documentElement: new FakeElement('html'),
  head,
  createElement(tag) { return new FakeElement(tag) },
  querySelector(selector) {
    if (selector === 'style[data-plugin="dsh-whale-animation"]') {
      return head.children.find(child => child.dataset.plugin === 'dsh-whale-animation') ?? null
    }
    return null
  },
  querySelectorAll(selector) {
    if (selector.includes('_turnStatus') || selector.includes('.Md3f7G_turnStatus')) return [status]
    if (selector === '[data-dsh-whale-host="true"]') {
      return status.getAttribute('data-dsh-whale-host') === 'true' ? [status] : []
    }
    return []
  },
}
class FakeMutationObserver {
  constructor(callback) { this.callback = callback }
  observe() {}
  disconnect() { observerDisconnected = true }
}
const context = {
  window: {
    __ModuleLoader__: { load(value) { loaded = value } },
    matchMedia() { return motionQuery },
  },
  document,
  MutationObserver: FakeMutationObserver,
  Date: { now: () => now },
  setInterval(callback) { intervalCallback = callback; return 7 },
  clearInterval(id) { if (id === 7) intervalCleared = true },
  queueMicrotask(callback) { callback() },
  console,
}
vm.runInNewContext(source, context, { filename: 'lib/client.js' })
assert(loaded?.id === 'dsh-whale-animation' && typeof loaded.factory === 'function', 'Client module did not register')
const plugin = loaded.factory(() => { throw new Error('No imports expected') })
assert(plugin?.name === 'dsh-whale-animation', 'Client plugin name mismatch')
assert(typeof plugin.apply === 'function', 'Client plugin apply missing')
assert(plugin.resolveWhaleState('Classic whale animation') === 'classic', 'Classic keyword mapping failed')
assert(plugin.resolveWhaleState('Classic') === 'classic', 'Bare Classic alias mapping failed')
assert(plugin.resolveWhaleState('Original') === 'classic', 'Bare Original alias mapping failed')
assert(plugin.resolveWhaleState('经典') === 'classic', 'Bare Chinese Classic alias mapping failed')
assert(plugin.resolveWhaleState('原版') === 'classic', 'Bare Chinese Original alias mapping failed')
assert(plugin.resolveWhaleState('Processing original source file') === null, 'Original substring must not trigger Classic')
assert(plugin.resolveWhaleState('Searching the web') === 'sonar', 'Search keyword mapping failed')
assert(plugin.resolveWhaleState('Using tool: shell') === 'work', 'Tool keyword mapping failed')
assert(plugin.resolveWhaleState('Generating answer') === 'compose', 'Compose keyword mapping failed')
assert(plugin.resolveWhaleState('Retrying after error') === 'alert', 'Alert keyword mapping failed')
assert(plugin.resolveWhaleState('Deep diving...') === null, 'Default Deep diving label must allow playlist rotation')
assert(plugin.chooseWhaleState('Deep diving...', 0, false) === manifest.playlist[0], 'Playlist start state mismatch')
assert(plugin.chooseWhaleState('Deep diving...', manifest.playlistIntervalMs, false) === 'classic', 'Second preserved animation is not in the playlist')
assert(plugin.chooseWhaleState('Deep diving...', manifest.playlistIntervalMs + manifest.states.classic.loopDurationMs - 1, false) === 'classic', 'Classic is truncated before one complete loop')
assert(plugin.chooseWhaleState('Deep diving...', manifest.playlistIntervalMs * 2, false) === 'sonar', 'Playlist did not advance after the full Classic slot')
assert(plugin.chooseWhaleState('Deep diving...', manifest.playlistIntervalMs, true) === manifest.defaultState, 'Reduced-motion state must remain stable')

let dispose
plugin.apply({ effect(start) { dispose = start() } })
assert(typeof dispose === 'function', 'Client disposer missing')
assert(head.children.length === 1 && head.children[0].dataset.plugin === 'dsh-whale-animation', 'Plugin style was not installed')
const installedCss = head.children[0].textContent
for (const state of stateKeys) {
  const urls = expectedDataUrls.get(state)
  const animatedRule = `[data-dsh-whale-state="${state}"]::after { background-image: url("${urls.animated}"); animation:`
  const staticRule = `@media (prefers-reduced-motion: reduce) { [data-dsh-whale-host="true"][data-dsh-whale-state="${state}"]::after { background-image: url("${urls.static}"); } }`
  assert(installedCss.includes(animatedRule), `${state}: animated asset is mapped to the wrong state`)
  assert(installedCss.includes(staticRule), `${state}: static asset is not mapped inside reduced-motion CSS`)
  assert(installedCss.indexOf(urls.animated) === installedCss.lastIndexOf(urls.animated), `${state}: animated asset is embedded in more than one CSS rule`)
  assert(installedCss.indexOf(urls.static) === installedCss.lastIndexOf(urls.static), `${state}: static asset is embedded in more than one CSS rule`)
}
assert(status.getAttribute('data-dsh-whale-host') === 'true', 'Status host was not decorated')
assert(status.getAttribute('data-dsh-whale-state') === manifest.playlist[0], 'Initial playlist state was not applied')

now += manifest.playlistIntervalMs
intervalCallback()
assert(status.getAttribute('data-dsh-whale-state') === 'classic', 'Timed playlist did not reach the second preserved loop')
status._text = 'Using tool: shell'
intervalCallback()
assert(status.getAttribute('data-dsh-whale-state') === 'work', 'Explicit tool state did not override playlist')
status._text = 'Retrying after error'
intervalCallback()
assert(status.getAttribute('data-dsh-whale-state') === 'alert', 'Explicit error state did not override playlist')
motionQuery.matches = true
status._text = 'Deep diving...'
motionListener?.()
assert(status.getAttribute('data-dsh-whale-state') === manifest.defaultState, 'Reduced-motion mode did not freeze on default state')

dispose()
assert(intervalCleared, 'Client interval was not cleared')
assert(observerDisconnected, 'Mutation observer was not disconnected')
assert(head.children.length === 0, 'Plugin style was not disposed')
assert(status.getAttribute('data-dsh-whale-host') === null && status.getAttribute('data-dsh-whale-state') === null, 'Host attributes were not cleaned up')

console.log(JSON.stringify({
  ok: true,
  states: stateKeys,
  playlist: manifest.playlist,
  preservedStates: Object.keys(expectedLegacyGitBlobs),
  totalAnimatedBytes,
  totalStaticBytes,
  clientBytes: Buffer.byteLength(source),
}))
