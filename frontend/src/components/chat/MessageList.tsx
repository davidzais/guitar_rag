import { useEffect, useRef } from 'react'
import { Bot, MessageSquare } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { MessageBubble } from './MessageBubble'
import { ApiError } from '@/lib/api'
import type { Message } from '@/hooks/useChat'

interface Props {
  messages: Message[]
  isPending: boolean
  error: Error | null
}

export function MessageList({ messages, isPending, error }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isPending])

  const errorMessage =
    error instanceof ApiError && error.status === 429
      ? 'You have reached the question limit for this conversation.'
      : error
        ? 'Something went wrong. Please try again.'
        : null

  return (
    <div className="h-120 overflow-y-auto p-4 space-y-4">
      {messages.length === 0 && !isPending && !errorMessage && (
        <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
          <div className="bg-slate-100 rounded-full p-4">
            <MessageSquare className="size-8 text-slate-400" />
          </div>
          <p className="text-slate-500 text-sm">
            Your answers will appear here.
          </p>
        </div>
      )}
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}
      {isPending && (
        <div className="flex justify-start gap-3">
          <div className="bg-slate-100 rounded-full p-1.5 shrink-0 self-start mt-1">
            <Bot className="size-4 text-slate-600" />
          </div>
          <div className="bg-slate-50 border border-slate-200 rounded-2xl rounded-tl-sm px-4 py-3">
            <div className="flex gap-1 items-center h-5">
              <span className="size-2 bg-slate-400 rounded-full animate-bounce [animation-delay:0ms]" />
              <span className="size-2 bg-slate-400 rounded-full animate-bounce [animation-delay:150ms]" />
              <span className="size-2 bg-slate-400 rounded-full animate-bounce [animation-delay:300ms]" />
            </div>
          </div>
        </div>
      )}
      {errorMessage && (
        <Alert variant="destructive">
          <AlertDescription>{errorMessage}</AlertDescription>
        </Alert>
      )}
      <div ref={bottomRef} />
    </div>
  )
}