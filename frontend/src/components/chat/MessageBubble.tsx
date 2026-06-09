import { Bot } from 'lucide-react'
import type { Message } from '@/hooks/useChat'

interface Props {
  message: Message
}

export function MessageBubble({ message }: Props) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] bg-slate-800 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start gap-3">
      <div className="bg-slate-100 rounded-full p-1.5 shrink-0 self-start mt-1">
        <Bot className="size-4 text-slate-600" />
      </div>
      <div className="max-w-[85%] bg-slate-50 border border-slate-200 rounded-2xl rounded-tl-sm overflow-hidden">
        <div className="max-h-72 overflow-y-auto px-4 py-3 text-sm leading-relaxed text-slate-700 whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    </div>
  )
}