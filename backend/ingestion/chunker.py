from dataclasses import dataclass
import tiktoken
import structlog
import re
from dotenv import load_dotenv
from models.transcript import Transcript, Segment


load_dotenv()

FILTER_TEXT = ["[music]", "[singing]", ">>", "[applause]"]
PATTERN_CLEAN = re.compile("|".join(re.escape(f) for f in FILTER_TEXT))
MAX_CHUNK_SIZE = 400
ENCODING = tiktoken.get_encoding("cl100k_base")
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


@dataclass(frozen=True)
class BufferedSegment:
    text: str
    token_count: int
    start_time: float | None


def filter_transcript(segments: list[Segment]) -> list[Segment]:
    cleaned: list[Segment] = []
    for segment in segments:
        scrubbed_text = PATTERN_CLEAN.sub("", segment.text).strip()
        if scrubbed_text:
            cleant_segment = Segment(
                text=scrubbed_text, start=segment.start, duration=segment.duration
            )

            cleaned.append(cleant_segment)
    return cleaned


def chunk_transcript(transcript: Transcript) -> list[Chunk]:
    """Accumulate filtered segments into ~400-token chunks (tiktoken),
    recording the start time of the first segment in each chunk and
    copying video_id/title/url onto every chunk."""
    token_count = 0
    chunk_index = 0
    segment_buffer: list[BufferedSegment] = []
    chunk_list: list[Chunk] = []

    for segment in transcript.segments:
        tokens = ENCODING.encode(segment.text)
        # this is the token count for this segment
        segment_token_count = len(tokens)
        # this is the running total for this Chunk
        token_count += segment_token_count
        buffered_segment = BufferedSegment(
            text=segment.text,
            token_count=segment_token_count,
            start_time=segment.start,
        )
        segment_buffer.append(buffered_segment)
        # have we crossed the chunk size token boundary
        if token_count > MAX_CHUNK_SIZE:
            # get the overlap chunks
            overlap_segment_count = get_offset_segment_count(segment_buffer)
            overlap_segment_data = segment_buffer[-overlap_segment_count:]
            chunk = build_chunk(segment_buffer, transcript, chunk_index)
            chunk_index += 1
            segment_buffer = overlap_segment_data
            token_count = sum(seg.token_count for seg in segment_buffer)

            chunk_list.append(chunk)

    # if theres any leftover pieces well collect them here
    if len(segment_buffer) > 0:
        chunk = build_chunk(segment_buffer, transcript, chunk_index)
        chunk_list.append(chunk)

    return chunk_list


def build_chunk(
    buffer: list[BufferedSegment], transcript: Transcript, index: int
) -> Chunk:
    chunk = Chunk(
        text=" ".join(seg.text for seg in buffer),
        video_id=transcript.video_id,
        title=transcript.title,
        url=transcript.url,
        chunk_index=index,
        instructor=transcript.instructor,
        start_time=buffer[0].start_time
    )
    return chunk


def get_offset_segment_count(
    info_buffer: list[BufferedSegment], offset_token_size=OVERLAP_TOKEN_SIZE
) -> int:
    # iterate from the end of info_buffer and sum the token counts until we reach ~offset_token_size
    # which tells us how many segments to grab for the overlap in the Chunk
    token_count = 0
    segment_count = 0
    for item in info_buffer[::-1]:
        token_count += item.token_count
        segment_count += 1

        # if this is true we've gone back enough segments
        if token_count > offset_token_size:
            return segment_count

    return segment_count