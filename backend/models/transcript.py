from pydantic import BaseModel


class Segment(BaseModel):
    text: str
    start: float | None
    duration: float | None


class Transcript(BaseModel):
    title: str
    text: str  # full merged transcript
    instructor: str  # e.g. "jack_ruch"
    video_id: str
    url: str  # base YouTube URL
    language: str
    is_generated: bool
    char_count: int
    segments: list[Segment]