import { Parser } from 'n3'

const RDF_TYPE = 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type'
const RESULT_CLASS = 'http://example.org/Result'

export type SelectRow = Record<string, string>

function localName(uri: string): string {
  if (uri.includes('#')) {
    return uri.split('#').pop() ?? uri
  }
  return uri.split('/').pop() ?? uri
}

function termToText(term: { value: string }): string {
  return term.value
}

export function parseSelectResultTurtle(ttl: string): SelectRow[] {
  const parser = new Parser()
  const rows = new Map<string, Record<string, string[]>>()
  const resultSubjects = new Set<string>()

  const quads = parser.parse(ttl) as Array<{
    subject: { value: string }
    predicate: { value: string }
    object: { value: string }
  }>
  for (const quad of quads) {
    const subject = quad.subject.value
    const predicate = quad.predicate.value
    const object = quad.object.value

    if (predicate === RDF_TYPE && object === RESULT_CLASS) {
      resultSubjects.add(subject)
      if (!rows.has(subject)) {
        rows.set(subject, {})
      }
      continue
    }

    if (!rows.has(subject)) {
      rows.set(subject, {})
    }

    const key = localName(predicate)
    const map = rows.get(subject)
    if (!map) {
      continue
    }

    map[key] = map[key] ?? []
    map[key].push(termToText(quad.object))
  }

  const output: SelectRow[] = []
  for (const subject of resultSubjects) {
    const data = rows.get(subject) ?? {}
    const normalized: SelectRow = {}
    for (const [key, values] of Object.entries(data)) {
      normalized[key] = values.join(' | ')
    }
    output.push(normalized)
  }

  return output
}
