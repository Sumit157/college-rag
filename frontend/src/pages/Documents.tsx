import { FileText, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

export function DocumentsPage() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Documents</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Organise study material by subject and semester, then index it for
          semantic search.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Your library</CardTitle>
          <CardDescription>Uploaded and indexed study material.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed px-6 py-12 text-center">
            <FileText className="size-8 text-muted-foreground" aria-hidden="true" />
            <p className="mt-3 text-sm font-medium">No documents yet</p>
            <p className="mt-1 max-w-md text-sm text-muted-foreground">
              PDF, DOCX, PPTX and TXT uploads will be indexed with their subject,
              semester and page information so every answer stays traceable.
            </p>
            <Button variant="outline" className="mt-4" disabled>
              <Upload className="size-4" aria-hidden="true" />
              Upload document
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
