import { createFileRoute } from '@tanstack/react-router'
import { useChat } from '@/hooks/useChat'
import { ConversationHeader } from '@/components/chat/ConversationHeader'
import { MessageList } from '@/components/chat/MessageList'
import { MessageInput } from '@/components/chat/MessageInput'


export const Route = createFileRoute('/')({
  component: ChatPage,
})

function ChatPage() {
  const { messages, questionsRemaining, mutation, newConversation } = useChat()

  return (    
    <div className="min-h-screen bg-linear-to-br from-slate-100 via-sky-50 to-indigo-100 p-4 sm:p-8 flex justify-center items-start">      
      <div className="w-full max-w-2xl">
        <div className="bg-white rounded-2xl shadow-xl border border-slate-200 overflow-hidden">
          <ConversationHeader
            questionsRemaining={questionsRemaining}
            onNewConversation={newConversation}
          />
          <div className="p-4 border-b bg-slate-50/60">
            <MessageInput
              onSend={(message) => mutation.mutate(message)}
              isPending={mutation.isPending}
              disabled={questionsRemaining === 0}
            />
          </div>
          <MessageList
            messages={messages}
            isPending={mutation.isPending}
            error={mutation.error}
          />
        </div>
      </div>
    </div>
  )
}