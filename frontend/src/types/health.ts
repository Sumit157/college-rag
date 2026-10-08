export interface MongoHealth {
  status: string
  database: string
}

export interface OllamaHealth {
  status: string
  url: string
  models: string[]
  llm_model?: string | null
  embedding_model?: string | null
  configured_model_available?: boolean
}

export interface HealthResponse {
  status: string
  app: string
  mongo: MongoHealth
  ollama: OllamaHealth
}
