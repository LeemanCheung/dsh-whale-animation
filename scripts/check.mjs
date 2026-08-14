import { readFile, stat } from 'node:fs/promises'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import vm from 'node:vm'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const source = await readFile(resolve(root, 'lib/client.js'), 'utf8')
let loaded
const context = {
  window: { __ModuleLoader__: { load(value) { loaded = value } } },
}
vm.runInNewContext(source, context, { filename: 'lib/client.js' })
if (!loaded || loaded.id !== 'dsh-whale-animation' || typeof loaded.factory !== 'function') throw new Error('Client module did not register')
const plugin = loaded.factory(() => { throw new Error('No imports expected') })
if (!plugin || typeof plugin.apply !== 'function') throw new Error('Client plugin apply missing')
let appended
let removed = false
const style = { dataset: {}, textContent: '', remove() { removed = true } }
globalThis.document = {
  querySelector() { return null },
  createElement(tag) { if (tag !== 'style') throw new Error(`Unexpected tag: ${tag}`); return style },
  head: { appendChild(value) { appended = value } },
}
context.document = globalThis.document
let dispose
plugin.apply({ effect(start) { dispose = start() } })
if (appended !== style || !style.textContent.includes('[class*="_turnStatus"]::after')) throw new Error('Persistent style was not installed')
if (typeof dispose !== 'function') throw new Error('Client disposer missing')
dispose()
if (!removed) throw new Error('Client style was not disposed')
delete globalThis.document
const animated = await stat(resolve(root, 'assets/whale-dive.webp'))
const reduced = await stat(resolve(root, 'assets/whale-static.png'))
if (animated.size !== 1514022) throw new Error(`Unexpected WebP size: ${animated.size}`)
if (reduced.size < 100) throw new Error('Reduced-motion PNG is empty')
if (!source.includes('data:image/webp;base64,') || !source.includes('data:image/png;base64,')) throw new Error('Embedded data URLs missing')
console.log(JSON.stringify({ ok: true, moduleId: loaded.id, animatedBytes: animated.size, reducedBytes: reduced.size, clientBytes: Buffer.byteLength(source) }))
