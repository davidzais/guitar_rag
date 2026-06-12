from pydantic import BaseModel

class Source(BaseModel):
    title: str
    url: str
    instructor: str
    start_time: float | None
    snippet: str
