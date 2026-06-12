import { z } from 'zod'

export const SourceSchema = z.object({
    title: z.string(),
    url: z.string(),
    instructor: z.string(),
    snippet: z.string(),
    start_time: z.number().nullable()

})

export const ChatRequestSchema = z.object({
  conversation_id: z.string().uuid(), 
  message: z.string().min(1, { error: 'Message cannot be empty' }).max(4000, { error: 'Message must be 4000 characters or fewer' }),
})


export const ChatResponseSchema = z.object({
  reply: z.string(),
  questions_remaining: z.number().int().min(0),
  sources: z.array(SourceSchema),
})

export const ApiErrorSchema = z.object({
  detail: z.string(),
})

export type Source = z.infer<typeof SourceSchema>
export type ChatRequest = z.infer<typeof ChatRequestSchema>
export type ChatResponse = z.infer<typeof ChatResponseSchema>