import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const ci = await readFile(resolve(root, '.github/workflows/ci.yml'), 'utf8')
const release = await readFile(resolve(root, '.github/workflows/release.yml'), 'utf8')

assert.match(ci, /contents:\s*read/)
assert.match(ci, /npm run verify/)
assert.match(ci, /git diff --exit-code -- assets\/manifest\.json lib\/client\.js/)
assert.match(ci, /check-browser\.sh/)
assert.doesNotMatch(ci, /pip install|requirements\.txt|artwork-sources\/spout/)

assert.match(release, /contents:\s*write/)
assert.match(release, /Existing immutable release tag/)
assert.match(release, /refs\/tags\/\$TAG\^\{commit\}/)
assert.match(release, /git ls-remote origin/)
assert.match(release, /Release \$TAG already exists; refusing to overwrite it/)
assert.doesNotMatch(release, /git\s+push|--force|requirements\.txt/)
const browserGate = release.match(/- name: Run Chromium browser smoke test\r?\n([\s\S]*?)(?=\r?\n      - name:|$)/)
assert.ok(browserGate, 'release publication must run the Chromium browser gate')
assert.match(browserGate[1], /run: npm run check:browser/)
assert.doesNotMatch(browserGate[1], /continue-on-error:|if:/, 'the release browser gate must be unconditional and blocking')
assert.ok(browserGate.index < release.indexOf('- name: Publish GitHub release'), 'browser verification must precede publication')

console.log('Workflow policy passed for two-loop CI and release.')
