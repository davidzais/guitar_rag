import { useCallback, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { sendMessage } from '@/lib/api'
import type { Source } from '@/lib/schemas'
import { useAuth } from '@clerk/clerk-react'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string,
  sources: Source[]
}

export function useChat() {
  const { getToken } = useAuth() 
  const [conversationId, setConversationId] = useState(() => crypto.randomUUID())
  const [messages, setMessages] = useState<Message[]>([])
  const [questionsRemaining, setQuestionsRemaining] = useState<number | null>(null)

  const mutation = useMutation({
    mutationFn: async (message: string) => {
    const token = await getToken()
    return sendMessage({ conversation_id: conversationId, message }, token)
    },

    onMutate: (message) => {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'user', content: message, sources: [] },
      ])
    },
    onSuccess: (data) => {
      console.log(data)
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'assistant', content: data.reply, sources: data.sources },
      ])
      setQuestionsRemaining(data.questions_remaining)
    },
  })

  const newConversation = useCallback(() => {
    setConversationId(crypto.randomUUID())
    setMessages([])
    setQuestionsRemaining(null)
    mutation.reset()
  }, [mutation])

  return { messages, questionsRemaining, mutation, newConversation }
}