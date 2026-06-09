from dataclasses import dataclass
import tiktoken
import structlog
from pathlib import Path
import json
import re
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv


load_dotenv()

FILTER_TEXT = ["[music]", "[singing]", ">>", "[applause]"]
PATTERN_CLEAN = re.compile("|".join(re.escape(f) for f in FILTER_TEXT))
MAX_CHUNK_SIZE = 400
all_chunks = []
logger = structlog.get_logger()

@dataclass
class Chunk:
    text: str           # cleaned chunk text
    instructor: str     # e.g. "jack_ruch"
    video_id: str
    url: str            # base YouTube URL
    title: str          # from metadata.json
    start_time: float | None # seconds into video — used to build timestamp URL
    chunk_index: int  
    
def load_data_filelist():
    target_dir = Path(__file__).resolve().parents[2] / "data_gathering/transcripts/"
    files = [f for f in Path(target_dir).rglob("*") if f.is_file()]

    return files


def load_transcript(path: Path) -> str:
    with open(path, 'r') as file:
        transcript =  json.load(file)

    return transcript

def filter_transcript(segments: list[dict]):
    cleaned = []
    for segment in segments:        
        text = PATTERN_CLEAN.sub("", segment["text"]).strip()  
        if text:
            segment["text"] = text
            cleaned.append(segment)                                                        
    return cleaned


    
def chunk_transcript(data: dict) -> list[Chunk]:
    """Accumulate filtered segments into ~400-token chunks (tiktoken),
    recording the start time of the first segment in each chunk and
    copying video_id/title/url onto every chunk."""
    token_count = 0
    chunk_index = 0  
    text_buffer: list[str] = []
    chunk_list: list[Chunk] = []
    chunk_start_time: float = 0.0
    
    encoding = tiktoken.get_encoding("cl100k_base")
    for segment in data["segments"][0]:
        if not text_buffer:
            chunk_start_time = segment["start"]

        tokens = encoding.encode(segment["text"])
        text_buffer.append(segment["text"])
        token_count += len(tokens)
        if token_count > MAX_CHUNK_SIZE:                 
            chunk = Chunk(
                text = " ".join(text_buffer),
                video_id = data["video_id"],
                title = data["title"],
                url = data["url"],
                chunk_index = chunk_index,
                instructor = data["instructor"],
                start_time= chunk_start_time        
            )
            chunk_index += 1
            token_count = 0
            text_buffer = []          
            chunk_list.append(chunk)

    if len(text_buffer) > 0:
        chunk = Chunk(
                text = " ".join(text_buffer),
                video_id = data["video_id"],
                title = data["title"],
                url = data["url"],
                chunk_index = chunk_index,
                instructor = data["instructor"],
                start_time = chunk_start_time             
            )
        chunk_list.append(chunk)

    return chunk_list


def main():
    file_list = load_data_filelist()
    for path in file_list:
        try:
            transcript = load_transcript(path)  
            transcript["segments"][0] = filter_transcript(transcript["segments"][0])
            chunks = chunk_transcript(transcript) 
            

        except Exception as e:
            print( str(e)  )

if __name__ == '__main__':
    main()