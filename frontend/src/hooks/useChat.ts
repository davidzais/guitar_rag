import { useCallback, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { sendMessage } from '@/lib/api'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
}

export function useChat() {
  const [conversationId, setConversationId] = useState(() => crypto.randomUUID())
  const [messages, setMessages] = useState<Message[]>([])
  const [questionsRemaining, setQuestionsRemaining] = useState<number | null>(null)

  const mutation = useMutation({
    mutationFn: (message: string) =>
      sendMessage({ conversation_id: conversationId, message }),
    onMutate: (message) => {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'user', content: message },
      ])
    },
    onSuccess: (data) => {
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'assistant', content: data.reply },
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