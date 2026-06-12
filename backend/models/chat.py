from pydantic import BaseModel, Field
from models.source import Source


class ChatRequest(BaseModel):
    conversation_id: str
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str
    sources: list[Source]
    questions_remaining: int
