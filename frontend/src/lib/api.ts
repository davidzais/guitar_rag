import { ChatRequestSchema, ChatResponseSchema, ApiErrorSchema, type ChatRequest, type ChatResponse } from './schemas'

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'
const API_KEY = import.meta.env.VITE_API_KEY as string | undefined

export class ApiError extends Error {
  declare status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function sendMessage(request: ChatRequest): Promise<ChatResponse> {
  const body = ChatRequestSchema.parse(request)
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(API_KEY ? { Authorization: `Bearer ${API_KEY}` } : {}),
    },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const parsed = ApiErrorSchema.safeParse(await res.json().catch(() => ({})))
    const detail = parsed.success ? parsed.data.detail : 'Request failed'
    throw new ApiError(res.status, detail)
  }

  return ChatResponseSchema.parse(await res.json())
}