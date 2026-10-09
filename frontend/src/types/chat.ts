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
  conversation_id?: string | null
}

export interface ChatResponse {
  answer: string
  evidence: Evidence[]
  grounded: boolean
  conversation_id: string
}

export interface ChatFilters {
  subject?: string
  semester?: number
  document_id?: string
}

export interface ConversationTurn {
  id: string
  question: string
  answer: string
  grounded: boolean
  evidence: Evidence[]
  subject: string | null
  semester: number | null
  document_id: string | null
  created_at: string
}

export interface ConversationSummary {
  id: string
  title: string
  turn_count: number
  created_at: string
  updated_at: string
}

export interface ConversationDetail extends ConversationSummary {
  turns: ConversationTurn[]
}

export interface ConversationListResponse {
  items: ConversationSummary[]
}

export type StreamEvent =
  | {
      type: 'meta'
      question: string
      grounded: boolean
      evidence: Evidence[]
      conversation_id: string
    }
  | { type: 'token'; text: string }
  | {
      type: 'done'
      answer: string
      grounded: boolean
      evidence: Evidence[]
      conversation_id: string
    }
  | { type: 'error'; detail: string }
