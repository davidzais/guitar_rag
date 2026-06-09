import { z } from 'zod'

export const ChatRequestSchema = z.object({
  conversation_id: z.string().uuid(),
  message: z.string().min(1, { error: 'Message cannot be empty' }).max(4000, { error: 'Message must be 4000 characters or fewer' }),
})

export const ChatResponseSchema = z.object({
  reply: z.string(),
  questions_remaining: z.number().int().min(0),
})

export const ApiErrorSchema = z.object({
  detail: z.string(),
})

export type ChatRequest = z.infer<typeof ChatRequestSchema>
export type ChatResponse = z.infer<typeof ChatResponseSchema>