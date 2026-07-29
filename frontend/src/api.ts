import type {
  ChunkDetail,
  DocumentItem,
  ChunkListItem,
  JobItem,
  Paginated,
  SearchResult,
  StatusInfo,
  WatchDirItem,
} from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

export async function api<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const r = await fetch(path, opts)
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`
    try {
      const body = await r.json()
      if (body?.detail) msg = `${r.status}: ${body.detail}`
    } catch {
      // response body is not JSON, keep default msg
    }
    throw new ApiError(r.status, msg)
  }
  return r.json() as Promise<T>
}

export const fetchStatus = () => api<StatusInfo>('/api/status')

export const fetchProjects = () =>
  api<{ projects: string[] }>('/api/projects').then((r) => r.projects)

export interface SearchParams {
  query: string
  top_k?: number
  project?: string | null
  threshold?: number
  rerank?: boolean
}

export const search = (p: SearchParams) =>
  api<{ results: SearchResult[] }>('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      query: p.query,
      top_k: p.top_k ?? 10,
      project: p.project ?? null,
      threshold: p.threshold ?? 0.3,
      rerank: p.rerank ?? false,
    }),
  }).then((r) => r.results)

export const fetchChunk = (id: string) =>
  api<ChunkDetail>(`/api/chunks/${encodeURIComponent(id)}`)

export interface DocumentsParams {
  project?: string
  status?: string
  q?: string
  sort?: string
  order?: 'asc' | 'desc'
  page?: number
  page_size?: number
}

export const fetchDocuments = (p: DocumentsParams = {}) => {
  const qs = new URLSearchParams()
  if (p.project) qs.set('project', p.project)
  if (p.status) qs.set('status', p.status)
  if (p.q) qs.set('q', p.q)
  if (p.sort) qs.set('sort', p.sort)
  if (p.order) qs.set('order', p.order)
  if (p.page) qs.set('page', String(p.page))
  if (p.page_size) qs.set('page_size', String(p.page_size))
  return api<Paginated<DocumentItem>>(`/api/documents?${qs.toString()}`)
}

export interface ChunksParams {
  doc_id?: string
  project?: string
  chunk_type?: string
  q?: string
  page?: number
  page_size?: number
}

export const fetchChunks = (p: ChunksParams = {}) => {
  const qs = new URLSearchParams()
  if (p.doc_id) qs.set('doc_id', p.doc_id)
  if (p.project) qs.set('project', p.project)
  if (p.chunk_type) qs.set('chunk_type', p.chunk_type)
  if (p.q) qs.set('q', p.q)
  if (p.page) qs.set('page', String(p.page))
  if (p.page_size) qs.set('page_size', String(p.page_size))
  return api<Paginated<ChunkListItem>>(`/api/chunks?${qs.toString()}`)
}

export const fetchWatchDirs = () =>
  api<{ items: WatchDirItem[] }>('/api/watch-dirs').then((r) => r.items)

export interface JobsParams {
  status?: string
  limit?: number
}

export const fetchJobs = (p: JobsParams = {}) => {
  const qs = new URLSearchParams()
  if (p.status) qs.set('status', p.status)
  if (p.limit) qs.set('limit', String(p.limit))
  return api<{ items: JobItem[] }>(`/api/jobs?${qs.toString()}`).then((r) => r.items)
}
