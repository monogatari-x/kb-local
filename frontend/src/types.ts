export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface DocumentItem {
  doc_id: string
  source_path: string
  rel_path: string
  project: string
  file_type: string
  language: string | null
  size_bytes: number
  ingested_at: string
  indexed_at: string | null
  status: string
}

export interface ChunkListItem {
  chunk_id: string
  doc_id: string
  chunk_type: string
  text_truncated: string | null
  start_line: number | null
  end_line: number | null
  language: string | null
  ordinal: number
}

export interface ChunkDetail {
  chunk_id: string
  doc_id: string
  chunk_type: string
  text: string
  start_line: number | null
  end_line: number | null
  language: string | null
  section_path: string | null
  symbol_path: string | null
}

export interface WatchDirItem {
  id: number
  path: string
  project_name: string
  project_strategy: string
  recursive: number
  file_types: string
  exclude_patterns: string
  include_patterns: string
  created_at: string
  last_scan_at: string | null
}

export interface JobItem {
  job_id: string
  type: string
  status: string
  started_at: string
  finished_at: string | null
  total_files: number | null
  processed_files: number
  failed_files: number
  error_log: string | null
  trigger: string | null
}

export interface SearchResult {
  text: string
  citation: string
  score: number
  chunk_type: string
  project: string | null
  chunk_id: string
}

export interface StatusInfo {
  documents: number
  chunks: number
  watch_dirs: number
  jobs: number
}
