import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type FormEvent,
} from 'react'
import {
  Eraser,
  Eye,
  Loader2,
  MessageSquare,
  Send,
  Square,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { apiFetch, ApiError } from '@/lib/api'
import { streamChat } from '@/lib/chat'
import type {
  ChatFilters,
  Evidence,
  StreamEvent,
} from '@/types/chat'
import type { DocumentItem, DocumentListResponse } from '@/types/document'

const SEMESTERS = Array.from({ length: 12 }, (_, i) => i + 1)

// Evidence at or above this relevance is presented as full support;
// between the server threshold (0.5) and this value we flag partial coverage.
// Measured on this corpus: related questions score >= 0.55, unrelated <= 0.49.
const FULL_SUPPORT_RELEVANCE = 0.55

type MessageStatus = 'searching' | 'thinking' | 'streaming' | 'done' | 'error'

interface Message {
  id: string
  role: 'user' | 'assistant'
  question?: string
  filters?: ChatFilters
  status?: MessageStatus
  answer?: string
  evidence?: Evidence[]
  grounded?: boolean
  error?: string
}

function applyStreamEvent(message: Message, event: StreamEvent): Message {
  switch (event.type) {
    case 'meta':
      return {
        ...message,
        status: event.grounded ? 'thinking' : 'done',
        evidence: event.evidence,
        grounded: event.grounded,
        answer: event.grounded ? (message.answer ?? '') : '',
      }
    case 'token':
      return {
        ...message,
        status: 'streaming',
        answer: (message.answer ?? '') + event.text,
      }
    case 'done':
      return {
        ...message,
        status: 'done',
        answer: event.answer,
        evidence: event.evidence,
        grounded: event.grounded,
        error: undefined,
      }
    case 'error':
      return {
        ...message,
        status: 'error',
        error: event.detail,
      }
  }
}

function sourceLocation(item: Evidence): string {
  const parts: string[] = []
  parts.push(item.page !== null ? `Page ${item.page}` : 'No page info')
  if (item.section) parts.push(item.section)
  return parts.join(' · ')
}

function GroundingBadge({
  message,
}: {
  message: Message
}) {
  if (message.status !== 'done') return null

  if (message.grounded === false) {
    return (
      <p className="flex items-center gap-2 rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground">
        <span aria-hidden="true">○</span>
        I couldn&apos;t find enough information in your uploaded material
      </p>
    )
  }

  const top = message.evidence?.[0]?.relevance ?? 0
  if (top < FULL_SUPPORT_RELEVANCE) {
    return (
      <p className="flex items-center gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-800 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200">
        <span aria-hidden="true">⚠</span>
        The uploaded material only partially covers this
      </p>
    )
  }

  return (
    <p className="flex items-center gap-2 rounded-md border border-green-300 bg-green-50 px-3 py-2 text-sm text-green-800 dark:border-green-700 dark:bg-green-950 dark:text-green-200">
      <span aria-hidden="true">✓</span>
      Answered from your study material
    </p>
  )
}

function ThinkingRow({ label }: { label: string }) {
  return (
    <p className="flex items-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="size-4 animate-spin" aria-hidden="true" />
      {label}
    </p>
  )
}

export function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)

  const [subject, setSubject] = useState<string>('all')
  const [semester, setSemester] = useState<string>('all')
  const [documentId, setDocumentId] = useState<string>('all')

  const [docs, setDocs] = useState<DocumentItem[]>([])

  const [source, setSource] = useState<Evidence | null>(null)

  const abortRef = useRef<AbortController | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    void (async () => {
      try {
        const data = await apiFetch<DocumentListResponse>('/documents')
        setDocs(data.items.filter((doc) => doc.status === 'indexed'))
      } catch {
        setDocs([])
      }
    })()
  }, [])

  useEffect(() => {
    const container = scrollRef.current
    if (container) container.scrollTop = container.scrollHeight
  }, [messages])

  const subjectOptions = Array.from(new Set(docs.map((doc) => doc.subject))).sort()

  const buildFilters = (): ChatFilters => {
    const filters: ChatFilters = {}
    if (subject !== 'all') filters.subject = subject
    if (semester !== 'all') filters.semester = Number(semester)
    if (documentId !== 'all') filters.document_id = documentId
    return filters
  }

  const patch = useCallback((id: string, next: (m: Message) => Message) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? next(m) : m)))
  }, [])

  const stop = () => {
    abortRef.current?.abort()
  }

  const send = async (event?: FormEvent) => {
    event?.preventDefault()
    const question = input.trim()
    if (!question || busy) return

    const filters = buildFilters()
    const userId = crypto.randomUUID()
    const assistantId = crypto.randomUUID()

    setMessages((prev) => [
      ...prev,
      { id: userId, role: 'user', question, filters },
      {
        id: assistantId,
        role: 'assistant',
        status: 'searching',
        answer: '',
        evidence: [],
        grounded: false,
      },
    ])
    setInput('')
    setBusy(true)

    const controller = new AbortController()
    abortRef.current = controller

    let sawMeta = false
    let sawDone = false
    let sawError = false

    try {
      await streamChat(
        { question, ...filters },
        controller.signal,
        {
          onEvent: (event) => {
            if (event.type === 'meta') sawMeta = true
            if (event.type === 'done') sawDone = true
            if (event.type === 'error') sawError = true
            patch(assistantId, (m) => applyStreamEvent(m, event))
          },
        },
      )
      if (controller.signal.aborted) {
        patch(assistantId, (m) =>
          sawMeta
            ? { ...m, status: 'done', grounded: m.grounded ?? false }
            : { ...m, status: 'error', error: 'Stopped before an answer arrived.' },
        )
      } else if (!sawDone && !sawError) {
        patch(assistantId, (m) => ({
          ...m,
          status: 'error',
          error: 'The connection ended unexpectedly. Please try again.',
        }))
      }
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : 'Something went wrong. Please try again.'
      patch(assistantId, (m) => ({ ...m, status: 'error', error: message }))
    } finally {
      setBusy(false)
      abortRef.current = null
    }
  }

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void send()
    }
  }

  const clearConversation = () => {
    if (busy) return
    setMessages([])
  }

  const filterLabel = (filters?: ChatFilters): string[] => {
    if (!filters) return []
    const labels: string[] = []
    if (filters.subject) labels.push(filters.subject)
    if (filters.semester) labels.push(`Semester ${filters.semester}`)
    if (filters.document_id) {
      const doc = docs.find((d) => d.id === filters.document_id)
      if (doc) labels.push(doc.filename)
    }
    return labels
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Ask questions about your uploaded material. Answers include the exact
            sources they were built from.
          </p>
        </div>
        {messages.length > 0 && (
          <Button
            variant="outline"
            size="sm"
            onClick={clearConversation}
            disabled={busy}
          >
            <Eraser className="size-4" aria-hidden="true" />
            Clear
          </Button>
        )}
      </div>

      <Card className="flex min-h-0 flex-1 flex-col">
        <CardContent ref={scrollRef} className="flex-1 overflow-y-auto py-4">
          {messages.length === 0 && (
            <div className="flex h-full flex-col items-center justify-center rounded-lg border border-dashed px-6 py-12 text-center">
              <MessageSquare className="size-8 text-muted-foreground" aria-hidden="true" />
              <p className="mt-3 text-sm font-medium">No questions yet</p>
              <p className="mt-1 max-w-md text-sm text-muted-foreground">
                Ask something about your study material and the assistant will
                answer with the supporting documents, pages and context.
              </p>
            </div>
          )}

          <div className="space-y-6">
            {messages.map((message) =>
              message.role === 'user' ? (
                <div key={message.id} className="flex flex-col items-end gap-1">
                  <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-primary px-4 py-2.5 text-sm text-primary-foreground">
                    <p className="whitespace-pre-wrap">{message.question}</p>
                  </div>
                  {filterLabel(message.filters).length > 0 && (
                    <div className="flex flex-wrap justify-end gap-1">
                      {filterLabel(message.filters).map((label) => (
                        <Badge key={label} variant="outline" className="text-xs">
                          {label}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div key={message.id} className="max-w-full space-y-3">
                  {message.status === 'searching' && (
                    <ThinkingRow label="Searching your library…" />
                  )}
                  {message.status === 'thinking' && (
                    <ThinkingRow label="Reviewing sources…" />
                  )}

                  {(message.status === 'streaming' ||
                    message.status === 'done' ||
                    message.status === 'error') &&
                    Boolean(message.answer) && (
                      <div className="text-sm leading-6 whitespace-pre-wrap">
                        {message.answer}
                        {message.status === 'streaming' && (
                          <span className="ml-0.5 inline-block animate-pulse text-muted-foreground">
                            ▍
                          </span>
                        )}
                      </div>
                    )}

                  <GroundingBadge message={message} />

                  {message.status === 'error' && (
                    <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                      {message.error}
                    </p>
                  )}

                  {message.status === 'done' &&
                    message.grounded === true &&
                    (message.evidence?.length ?? 0) > 0 && (
                      <div className="space-y-2">
                        <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                          Supported by
                        </p>
                        <div className="grid gap-2 sm:grid-cols-2">
                          {message.evidence?.map((item, index) => (
                            <button
                              key={item.id}
                              type="button"
                              onClick={() => setSource(item)}
                              className="group rounded-md border bg-muted/30 px-3 py-2 text-left transition-colors hover:bg-muted"
                            >
                              <p className="truncate text-sm font-medium">
                                <span className="mr-1 text-muted-foreground">
                                  [{index + 1}]
                                </span>
                                {item.filename}
                              </p>
                              <p className="truncate text-xs text-muted-foreground">
                                {sourceLocation(item)}
                              </p>
                              <p className="mt-1 flex items-center justify-between text-xs text-muted-foreground">
                                <span>
                                  Relevance {(item.relevance * 100).toFixed(0)}%
                                </span>
                                <span className="flex items-center gap-1 text-foreground opacity-0 transition-opacity group-hover:opacity-100">
                                  <Eye className="size-3" aria-hidden="true" />
                                  View source
                                </span>
                              </p>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                </div>
              ),
            )}
            <div ref={bottomRef} />
          </div>
        </CardContent>
      </Card>

      <form onSubmit={(event) => void send(event)} className="mt-3 space-y-2">
        <Textarea
          placeholder="Ask a question about your study material… (Enter to send, Shift+Enter for a new line)"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={onKeyDown}
          maxLength={2000}
          className="min-h-20 resize-none"
          disabled={busy}
        />
        <div className="flex flex-wrap items-center gap-2">
          <Select value={subject} onValueChange={setSubject}>
            <SelectTrigger className="w-44" aria-label="Subject filter">
              <SelectValue placeholder="Subject" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All subjects</SelectItem>
              {subjectOptions.map((name) => (
                <SelectItem key={name} value={name}>
                  {name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={semester} onValueChange={setSemester}>
            <SelectTrigger className="w-36" aria-label="Semester filter">
              <SelectValue placeholder="Semester" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All semesters</SelectItem>
              {SEMESTERS.map((n) => (
                <SelectItem key={n} value={String(n)}>
                  Sem {n}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={documentId} onValueChange={setDocumentId}>
            <SelectTrigger className="w-48" aria-label="Document filter">
              <SelectValue placeholder="Document" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All documents</SelectItem>
              {docs.map((doc) => (
                <SelectItem key={doc.id} value={doc.id}>
                  {doc.filename}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <div className="ml-auto">
            {busy ? (
              <Button type="button" variant="outline" onClick={stop}>
                <Square className="size-4" aria-hidden="true" />
                Stop
              </Button>
            ) : (
              <Button type="submit" disabled={!input.trim()}>
                <Send className="size-4" aria-hidden="true" />
                Send
              </Button>
            )}
          </div>
        </div>
        <p className="text-right text-xs text-muted-foreground">
          Answers use only your uploaded study material — never outside knowledge.
        </p>
      </form>

      <Dialog open={source !== null} onOpenChange={(open) => !open && setSource(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{source?.filename ?? 'Source'}</DialogTitle>
            <DialogDescription>
              {source ? sourceLocation(source) : ''}
            </DialogDescription>
          </DialogHeader>
          {source && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div>
                  <p className="text-muted-foreground">Page</p>
                  <p className="font-medium">{source.page ?? '—'}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Section</p>
                  <p className="font-medium">{source.section ?? '—'}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Relevance</p>
                  <p className="font-medium">
                    {(source.relevance * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
              <div>
                <p className="mb-2 text-sm font-medium">Retrieved text</p>
                <div className="max-h-72 overflow-y-auto rounded-md border bg-muted/40 px-3 py-2 text-sm whitespace-pre-wrap">
                  {source.text}
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
