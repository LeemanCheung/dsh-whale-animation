import { readFile, mkdir, writeFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const animated = (await readFile(resolve(root, 'assets/whale-dive.webp'))).toString('base64')
const reduced = (await readFile(resolve(root, 'assets/whale-static.png'))).toString('base64')
const animatedUrl = `data:image/webp;base64,${animated}`
const reducedUrl = `data:image/png;base64,${reduced}`
const css = `
.Md3f7G_turnStatus,
[class*="_turnStatus"] {
  position: relative;
}
.Md3f7G_turnStatus::before,
[class*="_turnStatus"]::before {
  content: none;
}
.Md3f7G_turnStatus::after,
[class*="_turnStatus"]::after {
  content: "";
  position: absolute;
  pointer-events: none;
  left: 100%;
  margin-left: 8px;
  top: 50%;
  margin-top: -46px;
  width: 92px;
  height: 92px;
  background-image: url("${animatedUrl}");
  background-position: center;
  background-size: contain;
  background-repeat: no-repeat;
  filter: none;
  -webkit-mask: none;
  mask: none;
  contain: paint;
}
@media (prefers-reduced-motion: reduce) {
  .Md3f7G_turnStatus::after,
  [class*="_turnStatus"]::after {
    background-image: url("${reducedUrl}");
  }
}
`

const client = `window.__ModuleLoader__.load({\n  id: "dsh-whale-animation",\n  factory: (require) => {\n    var module = { exports: {} };\n    var exports = module.exports;\n    const css = ${JSON.stringify(css)};\n    function apply(ctx) {\n      ctx.effect(() => {\n        const previous = document.querySelector('style[data-plugin="dsh-whale-animation"]');\n        if (previous) previous.remove();\n        const style = document.createElement('style');\n        style.dataset.plugin = 'dsh-whale-animation';\n        style.textContent = css;\n        document.head.appendChild(style);\n        return () => style.remove();\n      }, 'dsh-whale-animation: persistent style');\n    }\n    exports.apply = apply;\n    exports.name = 'dsh-whale-animation';\n    return module.exports;\n  }\n});\n`

await mkdir(resolve(root, 'lib'), { recursive: true })
await writeFile(resolve(root, 'lib/client.js'), client, 'utf8')
console.log(JSON.stringify({ animatedBytes: Buffer.byteLength(animated, 'base64'), reducedBytes: Buffer.byteLength(reduced, 'base64'), clientBytes: Buffer.byteLength(client) }))
