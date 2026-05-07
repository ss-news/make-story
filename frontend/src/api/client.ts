/**
 * Lightweight fetch wrapper for the make-story backend.
 *
 * Backend contract (Group C):
 *   - Success: 2xx with `{"data": ...}`
 *   - Error:   non-2xx with `{"error": {"code","message","fields"}}`
 *   - Auth: HttpOnly+Lax `sid` cookie (we always send credentials).
 */

export class ApiError extends Error {
  code: string
  status: number
  fields?: Record<string, string>

  constructor(
    status: number,
    code: string,
    message: string,
    fields?: Record<string, string>,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })

  const body = await res.json().catch(() => ({} as Record<string, unknown>))

  if (!res.ok) {
    const err = (body as { error?: { code?: string; message?: string; fields?: Record<string, string> } })
      .error ?? { code: 'UNKNOWN', message: res.statusText }
    throw new ApiError(res.status, err.code ?? 'UNKNOWN', err.message ?? res.statusText, err.fields)
  }

  return (body as { data: T }).data
}
