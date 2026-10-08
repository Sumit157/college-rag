import { MessageSquare } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'

export function ChatPage() {
  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Chat</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Ask questions about your uploaded material. Answers include the exact
          sources they were built from.
        </p>
      </div>

      <Card className="flex-1">
        <CardHeader>
          <CardTitle className="text-base">Conversation</CardTitle>
          <CardDescription>
            Answers are grounded in your documents only.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed px-6 py-12 text-center">
            <MessageSquare className="size-8 text-muted-foreground" aria-hidden="true" />
            <p className="mt-3 text-sm font-medium">No questions yet</p>
            <p className="mt-1 max-w-md text-sm text-muted-foreground">
              Ask something about your study material and the assistant will
              answer with the supporting documents, pages and context.
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="mt-4">
        <Textarea
          placeholder="Ask a question about your study material…"
          className="min-h-24 resize-none"
          disabled
        />
        <p className="mt-2 text-right text-xs text-muted-foreground">
          The question composer becomes available once chat is connected.
        </p>
      </div>
    </div>
  )
}
