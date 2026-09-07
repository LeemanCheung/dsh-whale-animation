import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const root=fileURLToPath(new URL('../',import.meta.url))
assert.ok(process.env.npm_execpath,'Run npm run check:package')
const packed=JSON.parse(execFileSync(process.execPath,[process.env.npm_execpath,'pack','--dry-run','--ignore-scripts','--json'],{cwd:root,encoding:'utf8'}))[0]
const paths=packed.files.map(file=>file.path)
const exact=new Set(['package.json','cordis.patch.yml','CHANGELOG.md','README.md','README.zh-CN.md','LICENSE','NOTICE.md','COMPATIBILITY.md','DESIGN.md','requirements-art.txt'])
for(const path of paths){
  assert.ok(exact.has(path)||/^(assets|lib|src|scripts|\.github\/workflows|artwork-sources\/four-actions|docs\/four-actions)\//.test(path),`Unexpected package entry: ${path}`)
  assert.ok(!/(^|\/)(node_modules|\.artifacts|output|__pycache__|diagnostics|credentials)(\/|\.)/i.test(path),`Private build material: ${path}`)
  assert.ok(!/\.svg$/i.test(path),`No SVG artwork: ${path}`)
}
for(const state of ['dive','classic','scout','surge','flow','breathe']){
  for(const ext of ['png','webp'])assert.ok(paths.includes(`assets/whale-${state}.${ext}`))
}
for(const state of ['scout','surge','flow','breathe']){
  assert.ok(!paths.includes(`artwork-sources/four-actions/${state}.png`), 'raw generation sheets stay in Git, not the runtime package')
  assert.ok(paths.includes(`artwork-sources/four-actions/${state}-report.json`))
}
assert.ok(paths.includes('artwork-sources/four-actions/prompts.json'))
assert.ok(packed.size<8*1024*1024,'Package exceeds 8 MiB')
console.log(JSON.stringify({ok:true,files:paths.length,bytes:packed.size}))
