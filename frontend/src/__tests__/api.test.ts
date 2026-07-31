import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api, ApiError } from '../api'

describe('api', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('returns parsed JSON on 2xx', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    )
    const out = await api<{ ok: boolean }>('/api/x')
    expect(out.ok).toBe(true)
  })

  it('throws ApiError on non-2xx with detail message', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify({ detail: 'nope' }), { status: 503 }),
    )
    await expect(api('/api/x')).rejects.toMatchObject({
      name: 'ApiError',
      status: 503,
      message: '503: nope',
    })
  })

  it('falls back to statusText when body is not JSON', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response('plain', { status: 500, statusText: 'Internal Server Error' }),
    )
    await expect(api('/api/x')).rejects.toMatchObject({
      status: 500,
      message: '500 Internal Server Error',
    })
  })
})

describe('ApiError', () => {
  it('captures status and message', () => {
    const e = new ApiError(404, 'not found')
    expect(e.status).toBe(404)
    expect(e.message).toBe('not found')
    expect(e.name).toBe('ApiError')
    expect(e).toBeInstanceOf(Error)
  })
})
