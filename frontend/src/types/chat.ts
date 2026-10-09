export interface Evidence {
  id: string
  document_id: string
  filename: string
  page: number | null
  section: string | null
  chunk_id: string
  text: string
  relevance: number
}

export interface ChatRequest {
  question: string
  subject?: string
  semester?: number
  document_id?: string
  top_k?: number
}

export interface ChatResponse {
  answer: string
  evidence: Evidence[]
  grounded: boolean
}

export interface ChatFilters {
  subject?: string
  semester?: number
  document_id?: string
}

export type StreamEvent =
  | { type: 'meta'; question: string; grounded: boolean; evidence: Evidence[] }
  | { type: 'token'; text: string }
  | { type: 'done'; answer: string; grounded: boolean; evidence: Evidence[] }
  | { type: 'error'; detail: string }
