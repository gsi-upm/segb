export type DecodedToken = {
  username?: string
  name?: string
  roles?: string[]
  exp?: number
}

function base64UrlDecode(value: string): string {
  const normalized = value.replace(/-/g, '+').replace(/_/g, '/')
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')
  return atob(padded)
}

export function decodeTokenPayload(token: string): DecodedToken | null {
  try {
    const parts = token.split('.')
    if (parts.length < 2) {
      return null
    }
    const payloadPart = parts[1]
    if (!payloadPart) {
      return null
    }

    const payloadText = base64UrlDecode(payloadPart)
    const parsed = JSON.parse(payloadText)
    if (typeof parsed !== 'object' || parsed === null) {
      return null
    }
    const roleValue = (parsed as Record<string, unknown>).roles
    const roles = Array.isArray(roleValue) ? roleValue.filter((role): role is string => typeof role === 'string') : undefined

    return {
      username: typeof parsed.username === 'string' ? parsed.username : undefined,
      name: typeof parsed.name === 'string' ? parsed.name : undefined,
      roles,
      exp: typeof parsed.exp === 'number' ? parsed.exp : undefined,
    }
  } catch {
    return null
  }
}

export function isTokenExpired(token: string): boolean {
  const decoded = decodeTokenPayload(token)
  if (!decoded?.exp) {
    return false
  }
  const now = Math.floor(Date.now() / 1000)
  return decoded.exp <= now
}
