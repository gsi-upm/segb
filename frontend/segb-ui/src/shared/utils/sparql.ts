const READ_ONLY_QUERY = /^\s*(SELECT|CONSTRUCT|ASK|DESCRIBE)\b/i
const UPDATE_QUERY = /^\s*(INSERT|DELETE|LOAD|CLEAR|DROP|CREATE|COPY|MOVE|ADD)\b/i

export function isReadOnlySparql(query: string): boolean {
  if (!READ_ONLY_QUERY.test(query)) {
    return false
  }
  return !UPDATE_QUERY.test(query)
}

export function getSparqlQueryKind(query: string): 'select' | 'construct' | 'ask' | 'describe' | 'unknown' {
  const match = query.trim().match(/^(SELECT|CONSTRUCT|ASK|DESCRIBE)\b/i)
  const verb = match?.[1]
  if (!verb) {
    return 'unknown'
  }
  return verb.toLowerCase() as 'select' | 'construct' | 'ask' | 'describe'
}
