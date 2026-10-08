import { RefreshCw } from 'lucide-react'
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
import { apiBase } from '@/lib/api'

function StatusRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2 text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}

export function SettingsPage() {
  const { health, loading, error, refresh } = useHealth()

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Runtime configuration and service health.
          </p>
        </div>
        <Button variant="outline" onClick={refresh} disabled={loading}>
          <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
          Refresh
        </Button>
      </div>

      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Application</CardTitle>
            <CardDescription>Local-first college study assistant.</CardDescription>
          </CardHeader>
          <CardContent className="divide-y">
            <StatusRow label="App" value={health?.app ?? '—'} />
            <StatusRow label="API base" value={apiBase()} />
            <StatusRow
              label="Health"
              value={loading ? 'checking…' : (health?.status ?? 'unavailable')}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">MongoDB</CardTitle>
            <CardDescription>Documents, chunks and vector search.</CardDescription>
          </CardHeader>
          <CardContent className="divide-y">
            {loading && (
              <>
                <Skeleton className="my-2 h-5 w-full" />
                <Skeleton className="my-2 h-5 w-full" />
              </>
            )}
            {!loading && health && (
              <>
                <StatusRow label="Database" value={health.mongo.database} />
                <div className="flex items-center justify-between gap-4 py-2 text-sm">
                  <span className="text-muted-foreground">Connection</span>
                  <Badge variant={health.mongo.status === 'ok' ? 'default' : 'destructive'}>
                    {health.mongo.status}
                  </Badge>
                </div>
              </>
            )}
            {!loading && !health && (
              <p className="py-2 text-sm text-muted-foreground">
                {error ?? 'Unavailable.'}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ollama</CardTitle>
            <CardDescription>Local LLM and embedding runtime.</CardDescription>
          </CardHeader>
          <CardContent className="divide-y">
            {loading && (
              <>
                <Skeleton className="my-2 h-5 w-full" />
                <Skeleton className="my-2 h-5 w-full" />
                <Skeleton className="my-2 h-5 w-2/3" />
              </>
            )}
            {!loading && health && (
              <>
                <StatusRow label="Endpoint" value={health.ollama.url} />
                <StatusRow
                  label="LLM model"
                  value={health.ollama.llm_model ?? '—'}
                />
                <StatusRow
                  label="Embedding model"
                  value={health.ollama.embedding_model ?? '—'}
                />
                <div className="flex items-center justify-between gap-4 py-2 text-sm">
                  <span className="text-muted-foreground">Connection</span>
                  <Badge variant={health.ollama.status === 'ok' ? 'default' : 'destructive'}>
                    {health.ollama.status}
                  </Badge>
                </div>
                <div className="py-2">
                  <p className="mb-2 text-sm text-muted-foreground">Local models</p>
                  <div className="flex flex-wrap gap-2">
                    {health.ollama.models.length > 0 ? (
                      health.ollama.models.map((model) => (
                        <Badge key={model} variant="outline">
                          {model}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-sm text-muted-foreground">None reported.</span>
                    )}
                  </div>
                </div>
              </>
            )}
            {!loading && !health && (
              <p className="py-2 text-sm text-muted-foreground">
                {error ?? 'Unavailable.'}
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
