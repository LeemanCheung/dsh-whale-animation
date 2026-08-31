import assert from 'node:assert/strict'
import { readdir, readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const workflowDir = resolve(root, '.github', 'workflows')
const names = (await readdir(workflowDir)).filter(name => /\.ya?ml$/i.test(name)).sort()
const workflows = new Map(await Promise.all(names.map(async name => [name, await readFile(resolve(workflowDir, name), 'utf8')])))

assert.ok(workflows.has('ci.yml'), 'ci.yml is missing')
assert.ok(workflows.has('release.yml'), 'release.yml is missing')

const forbidden = [
  /git\s+push[^\n]*HEAD:main/i,
  /git\s+push[^\n]*--force/i,
  /gh\s+release\s+delete/i,
  /git\s+tag\s+--delete/i,
  /git\s+checkout\s+-B\s+main/i,
]
for (const [name, text] of workflows) {
  for (const pattern of forbidden) assert.doesNotMatch(text, pattern, `${name} contains a forbidden release mutation`)
}

const writers = [...workflows].filter(([, text]) => /permissions:\s*\n\s+contents:\s*write\b/m.test(text)).map(([name]) => name)
assert.deepEqual(writers, ['release.yml'], 'only release.yml may receive contents: write')

const ci = workflows.get('ci.yml')
assert.match(ci, /contents:\s*read/)
assert.match(ci, /pip install[^\n]*-r requirements\.txt/)
assert.match(ci, /git diff --exit-code -- assets artwork-sources\/spout-imagegen-v1 lib\/client\.js/)
assert.match(ci, /git ls-files --others --exclude-standard/)

const release = workflows.get('release.yml')
assert.match(release, /tags:\s*\n\s+- ['"]v\*\.\*\.\*['"]/m)
assert.match(release, /Existing immutable release tag/)
assert.match(release, /pip install[^\n]*-r requirements\.txt/)
assert.match(release, /refs\/tags\/\$TAG\^\{commit\}/)
assert.match(release, /git ls-remote origin/)
assert.match(release, /npm run build:runtime-assets/)
assert.match(release, /git diff --exit-code -- assets artwork-sources\/spout-imagegen-v1 lib\/client\.js/)
assert.match(release, /artwork-sources\|__pycache__/)
assert.match(release, /git ls-files --others --exclude-standard/)
assert.match(release, /Release \$TAG already exists; refusing to overwrite it/)
assert.doesNotMatch(release, /branches:\s*\[?main\]?/)

console.log(`Workflow policy passed for ${workflows.size} workflows.`)
