from pydantic import BaseModel

class Transcript(BaseModel):
    title: str   
    text: str      # cleaned chunk text
    instructor: str     # e.g. "jack_ruch"
    video_id: str
    url: str            # base YouTube URL    
    language: str
    is_generated: bool    
    char_count: int
    instructor:str
    segments: list[Segment]   

class Segment(BaseModel):    
    text: str          # from metadata.json
    start: float | None
    duration: float | None