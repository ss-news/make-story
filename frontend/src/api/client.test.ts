import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { apiFetch, ApiError } from './client'

describe('apiFetch', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('returns body.data on success', async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ data: { id: '1', email: 'a@b.c' } }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await apiFetch<{ id: string; email: string }>('/api/auth/me')
    expect(result).toEqual({ id: '1', email: 'a@b.c' })
  })

  it('throws ApiError with status, code, fields on 4xx', async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          error: {
            code: 'VALIDATION',
            message: 'invalid input',
            fields: { email: 'required' },
          },
        }),
        { status: 400, headers: { 'Content-Type': 'application/json' } },
      ),
    )

    await expect(apiFetch('/api/auth/login', { method: 'POST' })).rejects.toMatchObject({
      status: 400,
      code: 'VALIDATION',
      message: 'invalid input',
      fields: { email: 'required' },
    })
    await expect(apiFetch('/api/auth/login', { method: 'POST' })).rejects.toBeInstanceOf(ApiError)
  })

  it('includes credentials: include and JSON content-type', async () => {
    const fetchMock = global.fetch as unknown as ReturnType<typeof vi.fn>
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ data: null }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    await apiFetch('/api/auth/me')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/auth/me',
      expect.objectContaining({
        credentials: 'include',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      }),
    )
  })
})
