const DATE_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  year: 'numeric',
  month: 'short',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
  timeZone: 'UTC',
})

export function compactUri(value: string | null | undefined): string {
  if (!value) {
    return ''
  }
  if (value.includes('#')) {
    return value.split('#').pop() ?? value
  }
  return value.replace(/\/$/, '').split('/').pop() ?? value
}

export function formatUtcTimestamp(raw: string | null | undefined): string {
  if (!raw) {
    return ''
  }
  const date = new Date(raw)
  if (Number.isNaN(date.getTime())) {
    return raw
  }
  return `${DATE_FORMATTER.format(date)} UTC`
}

export function toNumber(raw: string | null | undefined): number | null {
  if (!raw) {
    return null
  }
  const value = Number(raw)
  if (Number.isNaN(value)) {
    return null
  }
  return value
}

export function formatRatioAsPercent(raw: string | number | null | undefined, fractionDigits = 0): string {
  if (raw === null || raw === undefined || raw === '') {
    return ''
  }

  const value = typeof raw === 'number' ? raw : Number(raw)
  if (Number.isNaN(value)) {
    return String(raw)
  }

  if (value >= 0 && value <= 1) {
    return `${(value * 100).toFixed(fractionDigits)}%`
  }

  if (value > 1 && value <= 100) {
    return `${value.toFixed(fractionDigits)}%`
  }

  return value.toFixed(fractionDigits)
}

export function titleCase(value: string): string {
  return value
    .replace(/[_-]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase())
}
