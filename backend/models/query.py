from pydantic import BaseModel
from typing import Any

class MatchMetadata(BaseModel):
    chunk_index: int
    instructor: str
    start_time: float | None = None
    text: str
    title: str
    url: str
    video_id: str

class Match(BaseModel):
    id: str
    score: float    
    sparse_values: Any
    metadata: MatchMetadata

class Usage(BaseModel):
    read_units: int
    write_units: int | None

class QueryResponse(BaseModel):
    matches: list[Match]
    namespace: str
    usage: Usage
    response_info: dict | None = None