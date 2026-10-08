import { useCallback, useEffect, useState } from 'react'
import { apiFetch, ApiError } from '@/lib/api'
import type { HealthResponse } from '@/types/health'

interface UseHealthResult {
  health: HealthResponse | null
  loading: boolean
  error: string | null
  refresh: () => void
}

export function useHealth(): UseHealthResult {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const data = await apiFetch<HealthResponse>('/health')
      setHealth(data)
      setError(null)
    } catch (err: unknown) {
      setHealth(null)
      setError(err instanceof ApiError ? err.message : 'Health check failed.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { health, loading, error, refresh }
}
