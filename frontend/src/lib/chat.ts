import { apiBase, ApiError } from '@/lib/api'
import type { ChatRequest, StreamEvent } from '@/types/chat'

export interface StreamCallbacks {
  onEvent: (event: StreamEvent) => void
}

/**
 * POST /chat/stream and dispatch SSE events as they arrive.
 * Throws ApiError on transport or HTTP failures (message is user-safe).
 * Aborting via `signal` stops reading without an error.
 */
export async function streamChat(
  body: ChatRequest,
  signal: AbortSignal,
  callbacks: StreamCallbacks,
): Promise<void> {
  let response: Response
  try {
    response = await fetch(`${apiBase()}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    })
  } catch (err) {
    if (signal.aborted) return
    if (err instanceof DOMException && err.name === 'AbortError') return
    throw new ApiError('Cannot reach the backend server.', 0)
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status}).`
    try {
      const payload = (await response.json()) as { detail?: unknown }
      if (typeof payload.detail === 'string' && payload.detail.trim()) {
        detail = payload.detail
      }
    } catch {
      // keep the generic message
    }
    throw new ApiError(detail, response.status)
  }

  if (!response.body) {
    throw new ApiError('The server did not send a response stream.', 0)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  const dispatch = (block: string) => {
    for (const line of block.split('\n')) {
      if (!line.startsWith('data: ')) continue
      try {
        callbacks.onEvent(JSON.parse(line.slice(6)) as StreamEvent)
      } catch {
        // ignore malformed frames
      }
    }
  }

  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split('\n\n')
      buffer = blocks.pop() ?? ''
      for (const block of blocks) dispatch(block)
    }
    if (buffer.trim()) dispatch(buffer)
  } catch (err) {
    if (signal.aborted) return
    if (err instanceof DOMException && err.name === 'AbortError') return
    throw new ApiError('The connection was interrupted. Please try again.', 0)
  }
}
