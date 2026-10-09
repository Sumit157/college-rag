import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import {
  FileText,
  Loader2,
  Eye,
  Trash2,
  Upload,
  Search,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Skeleton } from '@/components/ui/skeleton'
import { apiFetch, apiUpload, ApiError } from '@/lib/api'
import type {
  ChunkItem,
  DocumentItem,
  DocumentListResponse,
} from '@/types/document'

const SEMESTERS = Array.from({ length: 12 }, (_, i) => i + 1)
const ACCEPT = '.pdf,.docx,.pptx,.txt'

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(iso: string): string {
  const date = new Date(iso)
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  })
}

function StatusBadge({ doc }: { doc: DocumentItem }) {
  switch (doc.status) {
    case 'indexed':
      return <Badge>Indexed</Badge>
    case 'processing':
      return <Badge variant="secondary">Processing</Badge>
    case 'failed':
      return <Badge variant="destructive">Failed</Badge>
    default:
      return <Badge variant="outline">Uploaded</Badge>
  }
}

export function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [file, setFile] = useState<File | null>(null)
  const [subject, setSubject] = useState('')
  const [semester, setSemester] = useState<string>('')
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [subjectFilter, setSubjectFilter] = useState<string>('all')
  const [semesterFilter, setSemesterFilter] = useState<string>('all')

  const [viewDoc, setViewDoc] = useState<DocumentItem | null>(null)
  const [chunks, setChunks] = useState<ChunkItem[]>([])
  const [chunksTotal, setChunksTotal] = useState(0)
  const [chunksLoading, setChunksLoading] = useState(false)

  const [deleteDoc, setDeleteDoc] = useState<DocumentItem | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const data = await apiFetch<DocumentListResponse>('/documents')
      setDocs(data.items)
      setError(null)
    } catch (err: unknown) {
      setError(err instanceof ApiError ? err.message : 'Could not load documents.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const subjectOptions = Array.from(new Set(docs.map((d) => d.subject))).sort()

  const visibleDocs = docs.filter((doc) => {
    if (subjectFilter !== 'all' && doc.subject !== subjectFilter) return false
    if (semesterFilter !== 'all' && doc.semester !== Number(semesterFilter)) return false
    return true
  })

  const openDetail = async (doc: DocumentItem) => {
    setViewDoc(doc)
    setChunks([])
    setChunksTotal(0)
    setChunksLoading(true)
    try {
      const data = await apiFetch<{ items: ChunkItem[]; total: number }>(
        `/documents/${doc.id}/chunks?limit=5`,
      )
      setChunks(data.items)
      setChunksTotal(data.total)
    } catch {
      setChunks([])
    } finally {
      setChunksLoading(false)
    }
  }

  const confirmDelete = async () => {
    if (!deleteDoc) return
    setDeleting(true)
    setDeleteError(null)
    try {
      await apiFetch<{ deleted: string }>(`/documents/${deleteDoc.id}`, {
        method: 'DELETE',
      })
      setDeleteDoc(null)
      await refresh()
    } catch (err: unknown) {
      setDeleteError(err instanceof ApiError ? err.message : 'Delete failed.')
    } finally {
      setDeleting(false)
    }
  }

  const onUpload = async (event: FormEvent) => {
    event.preventDefault()
    if (!file || !subject.trim() || !semester) {
      setUploadError('Choose a file, a subject and a semester.')
      return
    }
    setUploading(true)
    setUploadError(null)
    setUploadSuccess(null)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('subject', subject.trim())
    formData.append('semester', semester)
    try {
      const created = await apiUpload<DocumentItem>('/documents', formData)
      setUploadSuccess(
        `${created.filename} indexed — ${created.chunk_count} chunks stored.`,
      )
      setFile(null)
      setSemester('')
      if (fileInputRef.current) fileInputRef.current.value = ''
      await refresh()
    } catch (err: unknown) {
      setUploadError(err instanceof ApiError ? err.message : 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Documents</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Organise study material by subject and semester, then index it for
          semantic search.
        </p>
      </div>

      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">Upload study material</CardTitle>
          <CardDescription>
            PDF, DOCX, PPTX or TXT — files are parsed, chunked and stored with
            their page and section metadata.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={onUpload} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="sm:col-span-2 lg:col-span-1">
              <Input
                ref={fileInputRef}
                type="file"
                accept={ACCEPT}
                className="cursor-pointer"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
              <p className="mt-1 truncate text-xs text-muted-foreground">
                {file ? file.name : 'No file selected'}
              </p>
            </div>
            <Input
              placeholder="Subject (e.g. Operating Systems)"
              value={subject}
              onChange={(event) => setSubject(event.target.value)}
              maxLength={120}
            />
            <Select value={semester} onValueChange={setSemester}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Semester" />
              </SelectTrigger>
              <SelectContent>
                {SEMESTERS.map((n) => (
                  <SelectItem key={n} value={String(n)}>
                    Semester {n}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button type="submit" disabled={uploading}>
              {uploading ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  Indexing…
                </>
              ) : (
                <>
                  <Upload className="size-4" aria-hidden="true" />
                  Upload
                </>
              )}
            </Button>
          </form>
          {uploadError && (
            <p className="mt-3 rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {uploadError}
            </p>
          )}
          {uploadSuccess && (
            <p className="mt-3 rounded-md bg-green-600/10 px-3 py-2 text-sm text-green-700">
              {uploadSuccess}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-start justify-between gap-4">
          <div>
            <CardTitle className="text-base">Your library</CardTitle>
            <CardDescription>
              {docs.length} document{docs.length === 1 ? '' : 's'} indexed locally.
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Search className="size-4 text-muted-foreground" aria-hidden="true" />
            <Select value={subjectFilter} onValueChange={setSubjectFilter}>
              <SelectTrigger className="w-44">
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
            <Select value={semesterFilter} onValueChange={setSemesterFilter}>
              <SelectTrigger className="w-36">
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
          </div>
        </CardHeader>
        <CardContent>
          {loading && (
            <div className="space-y-2">
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-2/3" />
            </div>
          )}

          {!loading && error && (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {error}
            </p>
          )}

          {!loading && !error && docs.length === 0 && (
            <div className="flex flex-col items-center justify-center rounded-lg border border-dashed px-6 py-12 text-center">
              <FileText className="size-8 text-muted-foreground" aria-hidden="true" />
              <p className="mt-3 text-sm font-medium">No documents yet</p>
              <p className="mt-1 max-w-md text-sm text-muted-foreground">
                Upload a PDF, DOCX, PPTX or TXT file above to start building
                your study library.
              </p>
            </div>
          )}

          {!loading && !error && docs.length > 0 && visibleDocs.length === 0 && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No documents match the current filters.
            </p>
          )}

          {!loading && !error && visibleDocs.length > 0 && (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Document</TableHead>
                    <TableHead>Subject</TableHead>
                    <TableHead className="text-center">Sem</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Chunks</TableHead>
                    <TableHead>Uploaded</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {visibleDocs.map((doc) => (
                    <TableRow key={doc.id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <FileText className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                          <div className="min-w-0">
                            <p className="truncate font-medium">{doc.filename}</p>
                            <p className="text-xs uppercase text-muted-foreground">
                              {doc.file_type} · {formatBytes(doc.size_bytes)}
                              {doc.page_count ? ` · ${doc.page_count} pages` : ''}
                            </p>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>{doc.subject}</TableCell>
                      <TableCell className="text-center">{doc.semester}</TableCell>
                      <TableCell>
                        <StatusBadge doc={doc} />
                        {doc.status === 'failed' && doc.error && (
                          <p className="mt-1 max-w-52 text-xs text-destructive">
                            {doc.error}
                          </p>
                        )}
                      </TableCell>
                      <TableCell className="text-right">{doc.chunk_count}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatDate(doc.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => void openDetail(doc)}
                            aria-label={`View ${doc.filename}`}
                          >
                            <Eye className="size-4" aria-hidden="true" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setDeleteError(null)
                              setDeleteDoc(doc)
                            }}
                            aria-label={`Delete ${doc.filename}`}
                          >
                            <Trash2 className="size-4 text-destructive" aria-hidden="true" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={viewDoc !== null} onOpenChange={(open) => !open && setViewDoc(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{viewDoc?.filename ?? 'Document'}</DialogTitle>
            <DialogDescription>
              {viewDoc?.subject} · Semester {viewDoc?.semester}
            </DialogDescription>
          </DialogHeader>
          {viewDoc && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                <div>
                  <p className="text-muted-foreground">Status</p>
                  <p className="font-medium">
                    {viewDoc.status === 'indexed'
                      ? 'Indexed'
                      : viewDoc.status === 'failed'
                        ? 'Failed'
                        : viewDoc.status}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Chunks</p>
                  <p className="font-medium">{viewDoc.chunk_count}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Pages</p>
                  <p className="font-medium">{viewDoc.page_count ?? '—'}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Size</p>
                  <p className="font-medium">{formatBytes(viewDoc.size_bytes)}</p>
                </div>
              </div>

              {viewDoc.status === 'failed' && viewDoc.error && (
                <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {viewDoc.error}
                </p>
              )}

              <div>
                <p className="mb-2 text-sm font-medium">Indexed context</p>
                {chunksLoading && <Skeleton className="h-16 w-full" />}
                {!chunksLoading && chunks.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    No chunks stored for this document.
                  </p>
                )}
                {!chunksLoading && chunks.length > 0 && (
                  <div className="space-y-2">
                    {chunks.map((chunk) => (
                      <div
                        key={chunk.id}
                        className="rounded-md border bg-muted/40 px-3 py-2"
                      >
                        <p className="mb-1 text-xs text-muted-foreground">
                          {chunk.page ? `Page ${chunk.page}` : 'No pages'}
                          {chunk.section ? ` · ${chunk.section}` : ''}
                          {' · chunk '}
                          {chunk.chunk_index + 1}
                        </p>
                        <p className="line-clamp-3 text-sm">
                          {chunk.text.slice(0, 300)}
                          {chunk.text.length > 300 ? '…' : ''}
                        </p>
                      </div>
                    ))}
                    {chunksTotal > chunks.length && (
                      <p className="text-xs text-muted-foreground">
                        Showing first {chunks.length} of {chunksTotal} chunks.
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      <Dialog open={deleteDoc !== null} onOpenChange={(open) => !open && setDeleteDoc(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Delete document?</DialogTitle>
            <DialogDescription>
              This permanently removes <strong>{deleteDoc?.filename}</strong> and
              all of its indexed chunks from the library. This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          {deleteError && (
            <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
              {deleteError}
            </p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDoc(null)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={() => void confirmDelete()} disabled={deleting}>
              {deleting ? (
                <>
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                  Deleting…
                </>
              ) : (
                'Delete'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
