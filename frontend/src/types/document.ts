export type DocumentStatus = 'uploaded' | 'processing' | 'indexed' | 'failed'

export interface DocumentItem {
  id: string
  filename: string
  file_type: string
  file_hash: string
  subject: string
  semester: number
  status: DocumentStatus
  error: string | null
  chunk_count: number
  page_count: number | null
  size_bytes: number
  created_at: string
}

export interface ChunkItem {
  id: string
  document_id: string
  filename: string
  text: string
  page: number | null
  section: string | null
  subject: string
  semester: number
  chunk_index: number
}

export interface DocumentListResponse {
  items: DocumentItem[]
  total: number
}

export interface ChunkListResponse {
  items: ChunkItem[]
  total: number
}

export interface StatsResponse {
  documents: number
  subjects: number
}
