from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str
    questions_remaining: int
