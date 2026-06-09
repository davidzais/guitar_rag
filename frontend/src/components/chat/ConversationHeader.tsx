import { Bot, SquarePen } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface Props {
  questionsRemaining: number | null
  onNewConversation: () => void
}

export function ConversationHeader({ questionsRemaining, onNewConversation }: Props) {
  return (
    <header className="bg-linear-to-r from-slate-800 to-slate-700 px-5 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="bg-white/10 rounded-lg p-2">
          <Bot className="size-5 text-white" />
        </div>
        <div>
          <h1 className="text-white font-semibold text-sm leading-tight">
            Software Engineering Assistant
          </h1>
          <p className="text-slate-400 text-xs">Powered by Claude</p>
        </div>
      </div>
      <div className="flex items-center gap-2">
        {questionsRemaining !== null && (
          <Badge variant={questionsRemaining <= 2 ? 'destructive' : 'secondary'}>
            {questionsRemaining} question{questionsRemaining !== 1 ? 's' : ''} left
          </Badge>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={onNewConversation}
          title="New conversation"
          className="text-white hover:bg-white/10 hover:text-white"
        >
          <SquarePen />
        </Button>
      </div>
    </header>
  )
}
