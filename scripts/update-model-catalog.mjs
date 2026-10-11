// Refresh public capacity metadata only; this is not a model availability list.
// No local configuration, credentials or conversation data is read or sent.
import { createHash } from 'node:crypto'
import { writeFile } from 'node:fs/promises'

const source = 'https://models.dev/api.json'
const response = await fetch(source, { signal: AbortSignal.timeout(30_000) })
if (!response.ok) throw new Error(`Model catalog HTTP ${response.status}`)
const body = await response.text()
if (Buffer.byteLength(body) > 16 * 1024 * 1024) throw new Error('Model catalog is too large')
const catalog = JSON.parse(body)
const positive = value => Number.isSafeInteger(value) && value > 0
const providers = Object.entries(catalog).sort(([a], [b]) => a.localeCompare(b)).flatMap(([id, provider]) => {
  if (!provider || typeof provider !== 'object') return []
  const models = Object.entries(provider.models || {}).sort(([a], [b]) => a.localeCompare(b))
    .filter(([, model]) => positive(model?.limit?.context))
    .map(([name, model]) => [name, model.limit.context,
      positive(model.limit.input) ? model.limit.input : null,
      typeof model.canonical_model_id === 'string' ? model.canonical_model_id : ''])
  return models.length ? [[id, typeof provider.api === 'string' ? provider.api : '', models]] : []
})
const count = providers.reduce((total, [, , models]) => total + models.length, 0)
if (!count) throw new Error('Model catalog has no usable capacities')
const header = {
  source,
  license: 'MIT; https://github.com/anomalyco/models.dev/blob/dev/LICENSE',
  generated_at: new Date().toISOString(),
  source_sha256: createHash('sha256').update(body).digest('hex'),
  // Rows: provider id, API base, [model id, context, input limit, canonical id].
}
const content = `${JSON.stringify(header, null, 2).slice(0, -2)},\n  "providers": [\n${
  providers.map(provider => `    ${JSON.stringify(provider)}`).join(',\n')
}\n  ]\n}\n`
const target = new URL('../python/agent/models/catalog_snapshot.json', import.meta.url)
await writeFile(target, content)
console.log(`Updated ${providers.length} providers / ${count} capacities (${Buffer.byteLength(content)} bytes).`)
