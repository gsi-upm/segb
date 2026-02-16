export type ApiError = {
  statusCode: number | null
  message: string
  details?: string
}

export function normalizeApiError(error: unknown): ApiError {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof (error as Record<string, unknown>).response === 'object' &&
    (error as Record<string, unknown>).response !== null
  ) {
    const response = (error as Record<string, unknown>).response as Record<string, unknown>
    const statusCode = typeof response.status === 'number' ? response.status : null
    const data = (response.data ?? {}) as Record<string, unknown>
    const details = typeof data.detail === 'string' ? data.detail : undefined
    return {
      statusCode,
      message: details ?? 'Backend request failed.',
      details,
    }
  }

  if (error instanceof Error) {
    return {
      statusCode: null,
      message: error.message,
    }
  }

  return {
    statusCode: null,
    message: 'Unexpected frontend error.',
  }
}
