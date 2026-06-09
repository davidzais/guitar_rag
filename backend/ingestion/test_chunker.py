"""Unit tests for the transcript chunker.

Run these from the backend/ directory:
    uv run pytest ingestion/test_chunker.py -v

pytest auto-discovers anything named test_*.py, and inside it any function
named test_*. No registration, no base class needed — just write functions.
"""

from ingestion.chunker import Chunk, chunk_transcript, filter_transcript
from models.transcript import Transcript, Segment


def _make_transcript(segments: list[dict]) -> Transcript:
    """Build a Transcript shaped like real scraper output (flat segments).

    Pydantic coerces each plain dict into a `Segment`, so we can pass dicts
    here and get back a fully-typed `Transcript` — matching what
    `load_transcript` produces in production.
    """
    return Transcript(
        video_id="abc123",
        title="Test Lesson",
        url="https://www.youtube.com/watch?v=abc123",
        instructor="jack_ruch",
        text=" ".join(s["text"] for s in segments),
        language="en",
        is_generated=True,
        char_count=0,
        segments=segments,
    )


def test_drops_pure_noise_segments():
    # Arrange — build the smallest input that proves the behavior.
    # One real line of speech, plus one segment that is ONLY a [music] tag.
    segments = [
        Segment(text="today we play the blues", start=1.0, duration=2.0),
        Segment(text="[music]", start=3.0, duration=4.0),
    ]

    # Act — call the one function under test.
    result = filter_transcript(segments)

    # Assert — the music-only segment is gone, the real one survives.
    assert len(result) == 1
    assert result[0].text == "today we play the blues"


def test_strips_inline_marker_but_keeps_segment():
    # Arrange — a real line that happens to carry a ">>" speaker marker.
    segments = [
        Segment(text=">> so the G chord", start=5.0, duration=1.5),
    ]

    # Act
    result = filter_transcript(segments)

    # Assert — the marker is scrubbed, the words stay, and the timestamp
    # is preserved (the chunker needs `start` later for citations).
    assert len(result) == 1
    assert result[0].text == "so the G chord"
    assert result[0].start == 5.0


# ---------------------------------------------------------------------------
# chunk_transcript tests
#
# `monkeypatch` is a built-in pytest fixture — you get it just by naming it as
# a parameter. We use it to temporarily override MAX_CHUNK_SIZE so the test
# controls exactly where chunks split, instead of depending on the production
# value (which someone might change later). The override is undone
# automatically when the test ends.
# ---------------------------------------------------------------------------


def test_all_segments_fit_in_one_chunk(monkeypatch):
    # Arrange — a high limit so nothing splits. Three short segments that
    # together stay well under the limit should collapse into ONE chunk,
    # which only the trailing flush (after the loop) can produce.
    monkeypatch.setattr("ingestion.chunker.MAX_CHUNK_SIZE", 1000)
    transcript = _make_transcript([
        {"text": "we start on the G chord", "start": 0.0, "duration": 2.0},
        {"text": "then move to C", "start": 2.0, "duration": 1.5},
        {"text": "and finish on D", "start": 3.5, "duration": 1.5},
    ])

    # Act
    chunks = chunk_transcript(transcript)

    # Assert — exactly one chunk, texts space-joined in order...
    assert len(chunks) == 1
    chunk = chunks[0]
    assert isinstance(chunk, Chunk)
    assert chunk.text == "we start on the G chord then move to C and finish on D"
    # ...start_time is the FIRST segment's start, not the last...
    assert chunk.start_time == 0.0
    assert chunk.chunk_index == 0
    # ...and the video-level metadata was copied onto the chunk.
    assert chunk.video_id == "abc123"
    assert chunk.title == "Test Lesson"
    assert chunk.url == "https://www.youtube.com/watch?v=abc123"
    assert chunk.instructor == "jack_ruch"


def test_forced_split_one_chunk_per_segment(monkeypatch):
    # Arrange — a limit of 1 token forces every segment (each >1 token) to
    # flush on its own, so we get one chunk per segment. This exercises the
    # split path: chunk_index incrementing and a fresh start_time per chunk.
    monkeypatch.setattr("ingestion.chunker.MAX_CHUNK_SIZE", 1)
    transcript = _make_transcript([
        {"text": "alpha beta", "start": 0.0, "duration": 1.0},
        {"text": "gamma delta", "start": 10.0, "duration": 1.0},
        {"text": "epsilon zeta", "start": 20.0, "duration": 1.0},
    ])

    # Act
    chunks = chunk_transcript(transcript)

    # Assert — three chunks, each carrying its own segment, index, and start.
    assert len(chunks) == 3
    assert [c.text for c in chunks] == ["alpha beta", "gamma delta", "epsilon zeta"]
    assert [c.chunk_index for c in chunks] == [0, 1, 2]
    assert [c.start_time for c in chunks] == [0.0, 10.0, 20.0]