import { useState } from 'react'
import type { KeyboardEvent } from 'react'
import { Loader2, SendHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

interface Props {
  onSend: (message: string) => void
  isPending: boolean
  disabled: boolean
}

export function MessageInput({ onSend, isPending, disabled }: Props) {
  const [value, setValue] = useState('')

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || isPending || disabled) return
    onSend(trimmed)
    setValue('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <Textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={
          disabled
            ? 'Question limit reached for this conversation'
            : 'Ask a guitar playing question…'
        }
        disabled={isPending || disabled}
        rows={4}
        className="resize-none text-sm min-h-25"
      />
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Enter to send · Shift+Enter for newline
        </p>
        <Button
          onClick={handleSend}
          disabled={!value.trim() || isPending || disabled}
          className="gap-2"
        >
          {isPending ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <SendHorizontal className="size-4" />
          )}
          {isPending ? 'Thinking…' : 'Send'}
        </Button>
      </div>
    </div>
  )
}