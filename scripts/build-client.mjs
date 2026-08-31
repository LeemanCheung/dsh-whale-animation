import { readFile, mkdir, writeFile } from 'node:fs/promises'
import { dirname, extname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const manifestPath = resolve(root, 'assets/manifest.json')
const runtimePath = resolve(root, 'src/client-runtime.js')
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'))
const runtime = await readFile(runtimePath, 'utf8')

if (manifest.schemaVersion !== 1) throw new Error(`Unsupported asset manifest schema: ${manifest.schemaVersion}`)
if (!Array.isArray(manifest.playlist) || manifest.playlist.length === 0) throw new Error('Animation playlist is empty')
if (!manifest.states || typeof manifest.states !== 'object') throw new Error('Animation states are missing')
if (!manifest.states[manifest.defaultState]) throw new Error(`Default state does not exist: ${manifest.defaultState}`)

const stateKeys = Object.keys(manifest.states)
const animatedNames = new Set()
const staticNames = new Set()
const assets = {}
let sourceAssetBytes = 0
for (const state of stateKeys) {
  const entry = manifest.states[state]
  const expectedAnimated = `whale-${state}.webp`
  const expectedStatic = `whale-${state}.png`
  if (entry.animated !== expectedAnimated) throw new Error(`${state}: animated mapping must be ${expectedAnimated}, got ${entry.animated}`)
  if (entry.static !== expectedStatic) throw new Error(`${state}: static mapping must be ${expectedStatic}, got ${entry.static}`)
  if (animatedNames.has(entry.animated)) throw new Error(`${state}: animated asset is mapped more than once`)
  if (staticNames.has(entry.static)) throw new Error(`${state}: static asset is mapped more than once`)
  animatedNames.add(entry.animated)
  staticNames.add(entry.static)
  const animatedPath = resolve(root, 'assets', entry.animated)
  const staticPath = resolve(root, 'assets', entry.static)
  const animated = await readFile(animatedPath)
  const reduced = await readFile(staticPath)
  if (animated.subarray(0, 4).toString('ascii') !== 'RIFF' || animated.subarray(8, 12).toString('ascii') !== 'WEBP') {
    throw new Error(`${state}: animated mapping is not a WebP payload`)
  }
  if (!reduced.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) {
    throw new Error(`${state}: static mapping is not a PNG payload`)
  }
  sourceAssetBytes += animated.byteLength + reduced.byteLength
  const animatedMime = extname(animatedPath) === '.webp' ? 'image/webp' : 'application/octet-stream'
  const staticMime = extname(staticPath) === '.png' ? 'image/png' : 'application/octet-stream'
  assets[state] = {
    animated: `data:${animatedMime};base64,${animated.toString('base64')}`,
    static: `data:${staticMime};base64,${reduced.toString('base64')}`,
  }
}
for (const state of manifest.playlist) {
  if (!assets[state]) throw new Error(`Playlist references an unmapped state: ${state}`)
}

const hostSelector = '[data-dsh-whale-host="true"]'
const cssRules = [
  `${hostSelector} { position: relative !important; overflow: visible !important; }`,
  `${hostSelector}::after { content: ""; position: absolute; pointer-events: none; user-select: none; left: 100%; margin-left: 6px; top: 50%; width: 84px; height: 84px; transform: translateY(-50%); transform-origin: center; background-position: center; background-size: contain; background-repeat: no-repeat; opacity: .96; z-index: 1; contain: paint; }`,
]
for (const state of stateKeys) {
  cssRules.push(
    `@keyframes dsh-whale-switch-${state} { from { opacity: .42; transform: translateY(-50%) scale(.92); } to { opacity: .96; transform: translateY(-50%) scale(1); } }`,
    `${hostSelector}[data-dsh-whale-state="${state}"]::after { background-image: url("${assets[state].animated}"); animation: dsh-whale-switch-${state} 180ms cubic-bezier(.2,.8,.2,1); }`,
  )
}
cssRules.push(
  `@media (prefers-color-scheme: dark) { ${hostSelector}::after { filter: invert(1); } }`,
  `html.dark ${hostSelector}::after, html[data-theme="dark"] ${hostSelector}::after { filter: invert(1); }`,
  `@media (prefers-reduced-motion: reduce) { ${hostSelector}::after { animation: none !important; transition: none; } }`,
)
for (const state of stateKeys) {
  cssRules.push(`@media (prefers-reduced-motion: reduce) { ${hostSelector}[data-dsh-whale-state="${state}"]::after { background-image: url("${assets[state].static}"); } }`)
}
cssRules.push(
  `@media (max-width: 720px) { ${hostSelector}::after { width: 72px; height: 72px; margin-left: 4px; } }`,
  `@media (max-width: 480px) { ${hostSelector}::after { width: 60px; height: 60px; margin-left: 2px; } }`,
  `@media print { ${hostSelector}::after { display: none !important; } }`,
)
const css = `${cssRules.join('\n')}\n`

const replacements = new Map([
  ['__WHALE_STATE_KEYS__', JSON.stringify(stateKeys)],
  ['__WHALE_PLAYLIST__', JSON.stringify(manifest.playlist)],
  ['__WHALE_DEFAULT_STATE__', JSON.stringify(manifest.defaultState)],
  ['__WHALE_PLAYLIST_INTERVAL_MS__', JSON.stringify(manifest.playlistIntervalMs)],
  ['__WHALE_CSS__', JSON.stringify(css)],
])
let body = runtime
for (const [placeholder, value] of replacements) {
  if (!body.includes(placeholder)) throw new Error(`Runtime placeholder missing: ${placeholder}`)
  body = body.replaceAll(placeholder, value)
}
if (/__WHALE_[A-Z0-9_]+__/.test(body)) throw new Error('Unresolved runtime placeholder remains')

const client = `window.__ModuleLoader__.load({\n  id: "dsh-whale-animation",\n  factory: (require) => {\n    var module = { exports: {} };\n    var exports = module.exports;\n${body.split('\n').map(line => line === '' ? '' : `    ${line}`).join('\n')}\n    return module.exports;\n  }\n});\n`

await mkdir(resolve(root, 'lib'), { recursive: true })
await writeFile(resolve(root, 'lib/client.js'), client, 'utf8')
console.log(JSON.stringify({
  states: stateKeys,
  playlist: manifest.playlist,
  sourceAssetBytes,
  cssBytes: Buffer.byteLength(css),
  clientBytes: Buffer.byteLength(client),
}))
