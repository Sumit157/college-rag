import { ArrowRight, CheckCircle2, FileText, MessageSquare, XCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useHealth } from '@/hooks/useHealth'

export function DashboardPage() {
  const { health, loading, error, refresh } = useHealth()

  const mongoOk = health?.mongo.status === 'ok'
  const ollamaOk = health?.ollama.status === 'ok'

  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Your study material, retrievable and verifiable.
          </p>
        </div>
        <Button asChild>
          <Link to="/chat">
            Open Chat
            <ArrowRight className="size-4" aria-hidden="true" />
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Documents</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Subjects</CardDescription>
            <CardTitle className="text-3xl">0</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>MongoDB</CardDescription>
            <CardTitle className="text-3xl">
              {loading ? (
                <Skeleton className="h-8 w-16" />
              ) : mongoOk ? (
                <CheckCircle2 className="size-7 text-green-600" aria-label="Connected" />
              ) : (
                <XCircle className="size-7 text-destructive" aria-label="Unavailable" />
              )}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Ollama</CardDescription>
            <CardTitle className="text-3xl">
              {loading ? (
                <Skeleton className="h-8 w-16" />
              ) : ollamaOk ? (
                <CheckCircle2 className="size-7 text-green-600" aria-label="Connected" />
              ) : (
                <XCircle className="size-7 text-destructive" aria-label="Unavailable" />
              )}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Recent documents</CardTitle>
            <CardDescription>Your latest uploaded study material.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed px-6 py-10 text-center">
              <FileText className="size-8 text-muted-foreground" aria-hidden="true" />
              <p className="mt-3 text-sm font-medium">No documents yet</p>
              <p className="mt-1 max-w-sm text-sm text-muted-foreground">
                Upload PDFs, DOCX, PPTX or TXT files from the Documents page to
                start building your study library.
              </p>
              <Button asChild variant="outline" className="mt-4">
                <Link to="/documents">Go to Documents</Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">System status</CardTitle>
            <CardDescription>Local services used by the assistant.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm">
            {loading && (
              <>
                <Skeleton className="h-5 w-full" />
                <Skeleton className="h-5 w-full" />
                <Skeleton className="h-5 w-3/4" />
              </>
            )}
            {!loading && error && (
              <div className="rounded-md bg-destructive/10 px-3 py-2 text-destructive">
                {error}
              </div>
            )}
            {!loading && !error && health && (
              <>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground">Overall</span>
                  <Badge variant={health.status === 'ok' ? 'default' : 'destructive'}>
                    {health.status}
                  </Badge>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground">Database</span>
                  <Badge variant={mongoOk ? 'default' : 'destructive'}>
                    {health.mongo.status}
                  </Badge>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground">LLM runtime</span>
                  <Badge variant={ollamaOk ? 'default' : 'destructive'}>
                    {health.ollama.status}
                  </Badge>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground">LLM model</span>
                  <span className="font-medium">{health.ollama.llm_model ?? '—'}</span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-muted-foreground">Embedding model</span>
                  <span className="font-medium">
                    {health.ollama.embedding_model ?? '—'}
                  </span>
                </div>
                <Button variant="outline" size="sm" className="w-full" onClick={refresh}>
                  Refresh status
                </Button>
              </>
            )}
            {!loading && !error && !health && (
              <p className="text-muted-foreground">Status unavailable.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Ask your study material</CardTitle>
          <CardDescription>
            Every answer shows the exact documents and pages it came from.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button asChild variant="secondary">
            <Link to="/chat">
              <MessageSquare className="size-4" aria-hidden="true" />
              Start a question
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
