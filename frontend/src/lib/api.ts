import { ChatRequestSchema, ChatResponseSchema, ApiErrorSchema, type ChatRequest, type ChatResponse } from './schemas'

const API_BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

export class ApiError extends Error {
  declare status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function sendMessage(request: ChatRequest, token: string | null): Promise<ChatResponse> {
  const body = ChatRequestSchema.parse(request)
  let res: Response
  try {
          res = await fetch(`${API_BASE}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(body),
          signal: AbortSignal.timeout(90_000), //set a 90 second limit and then abort
          
        })
      }
      catch(err) {
         if (err instanceof DOMException && err.name === 'TimeoutError') {
             throw new ApiError(408, 'This is taking longer than expected — the app may be waking up. Please try again.')
         }
         throw err
      }
  
  if (!res.ok) {
    const parsed = ApiErrorSchema.safeParse(await res.json().catch(() => ({})))
    const detail = parsed.success ? parsed.data.detail : 'Request failed'
    throw new ApiError(res.status, detail)
  }
 
  return ChatResponseSchema.parse(await res.json())
}