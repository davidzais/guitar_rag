from dataclasses import dataclass
from pprint import pprint
import tiktoken
import structlog
from pathlib import Path
import json
import re
from dotenv import load_dotenv
from models.transcript import Transcript, Segment


load_dotenv()

FILTER_TEXT = ["[music]", "[singing]", ">>", "[applause]"]
PATTERN_CLEAN = re.compile("|".join(re.escape(f) for f in FILTER_TEXT))
MAX_CHUNK_SIZE = 400

OVERLAP_TOKEN_SIZE = 50  # NOTE this value should always be well below the MAX_CHUNK_SIZE, rith now its ~12% which is good
logger = structlog.get_logger()


@dataclass
class Chunk:
    text: str  # cleaned chunk text
    instructor: str  # e.g. "jack_ruch"
    video_id: str
    url: str  # base YouTube URL
    title: str  # from metadata.json
    start_time: float | None  # seconds into video — used to build timestamp URL
    chunk_index: int


def load_data_filelist():
    target_dir = Path(__file__).resolve().parents[2] / "data_gathering/transcripts/"
    files = [f for f in Path(target_dir).rglob("*") if f.is_file()]

    return files


def load_transcript(path: Path) -> Transcript:
    with open(path, "r") as file:
        return Transcript.model_validate(json.load(file))


def filter_transcript(segments: list[Segment]):
    cleaned = []
    for segment in segments:
        text = PATTERN_CLEAN.sub("", segment.text).strip()
        if text:
            segment.text = text
            cleaned.append(segment)
    return cleaned


def chunk_transcript(transcript: Transcript) -> list[Chunk]:
    """Accumulate filtered segments into ~400-token chunks (tiktoken),
    recording the start time of the first segment in each chunk and
    copying video_id/title/url onto every chunk."""
    token_count = 0
    chunk_index = 0
    text_buffer: list[dict] = []
    chunk_list: list[Chunk] = []

    encoding = tiktoken.get_encoding("cl100k_base")
    for segment in transcript.segments:
        tokens = encoding.encode(segment.text)

        segment_token_count = len(tokens)
        token_count += segment_token_count
        text_buffer.append(
            {
                "text": segment.text,
                "token_count": segment_token_count,
                "start_time": segment.start,
            }
        )
        if token_count > MAX_CHUNK_SIZE:
            # get the overlap chunks
            overlap_segment_count = get_offset_token_segment_count(text_buffer)
            overlap_segment_data = text_buffer[-overlap_segment_count:]
            chunk = Chunk(
                text=" ".join(seg["text"] for seg in text_buffer),
                video_id=transcript.video_id,
                title=transcript.title,
                url=transcript.url,
                chunk_index=chunk_index,
                instructor=transcript.instructor,
                start_time=text_buffer[0]["start_time"],
            )
            chunk_index += 1
            text_buffer = overlap_segment_data
            token_count = sum(seg["token_count"] for seg in text_buffer)

            chunk_list.append(chunk)

    if len(text_buffer) > 0:
        chunk = Chunk(
            text=" ".join(seg["text"] for seg in text_buffer),
            video_id=transcript.video_id,
            title=transcript.title,
            url=transcript.url,
            chunk_index=chunk_index,
            instructor=transcript.instructor,
            start_time=text_buffer[0]["start_time"],
        )
        chunk_list.append(chunk)

    return chunk_list


def get_offset_token_segment_count(
    info_buffer: list[dict], offset_token_size=OVERLAP_TOKEN_SIZE
):
    # iterate from the end of info_buffer and sum the token counts untile we reach ~offset_token_size
    # the number of
    token_count = 0
    segment_count = 0
    for item in info_buffer[::-1]:
        token_count += item["token_count"]
        segment_count += 1

        if token_count > offset_token_size:
            return segment_count

    return segment_count  # well always go back at least 1 chunk of data for overlap


def main():
    file_list = load_data_filelist()
    for path in file_list:
        try:
            transcript = load_transcript(path)
            transcript.segments = filter_transcript(transcript.segments)
            chunks = chunk_transcript(transcript)
            pprint(chunks)
            break

        except Exception as e:
            print(str(e))


if __name__ == "__main__":
    main()
