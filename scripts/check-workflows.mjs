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
assert.match(ci, /npm run art:check/)
assert.match(ci, /requirements-art\.txt/)
assert.match(ci, /npm run check:package/)
assert.doesNotMatch(ci, /artwork-sources\/spout/)

assert.match(release, /contents:\s*write/)
assert.match(release, /Existing immutable release tag/)
assert.match(release, /refs\/tags\/\$TAG\^\{commit\}/)
assert.match(release, /git ls-remote origin/)
assert.match(release, /Release \$TAG already exists; refusing to overwrite it/)
assert.doesNotMatch(release, /git\s+push|--force|requirements\.txt/)

console.log('Workflow policy passed for six-loop CI and release.')
