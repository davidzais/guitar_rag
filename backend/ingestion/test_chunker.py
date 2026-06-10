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
    transcript = _make_transcript(
        [
            {"text": "we start on the G chord", "start": 0.0, "duration": 2.0},
            {"text": "then move to C", "start": 2.0, "duration": 1.5},
            {"text": "and finish on D", "start": 3.5, "duration": 1.5},
        ]
    )

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


# ---------------------------------------------------------------------------
# Overlap tests
#
# We patch BOTH knobs so the ratio stays realistic in miniature: a small chunk
# size with an even smaller overlap. (If overlap >= chunk size, chunks grow
# without bound — see the OVERLAP_TOKEN_SIZE note in chunker.py.) We assert the
# overlap *property* — the seam between chunks — not exact token-dependent text,
# so these stay green even if tiktoken's counts shift.
# ---------------------------------------------------------------------------

# A dozen distinct words so overlap is spottable and nothing collides.
_WORDS = [
    "alpha",
    "bravo",
    "charlie",
    "delta",
    "echo",
    "foxtrot",
    "golf",
    "hotel",
    "india",
    "juliet",
    "kilo",
    "lima",
]


def _make_word_transcript() -> Transcript:
    """One word per segment, with increasing start times (0.0, 1.0, 2.0, ...)."""
    return _make_transcript(
        [{"text": w, "start": float(i), "duration": 1.0} for i, w in enumerate(_WORDS)]
    )


def test_split_produces_sequentially_indexed_chunks(monkeypatch):
    # Arrange — small chunk + small overlap forces several chunks.
    monkeypatch.setattr("ingestion.chunker.MAX_CHUNK_SIZE", 4)
    monkeypatch.setattr("ingestion.chunker.OVERLAP_TOKEN_SIZE", 1)

    # Act
    chunks = chunk_transcript(_make_word_transcript())

    # Assert — we got multiple chunks, indexes run 0,1,2,... with no gaps,
    # none are empty, and start times never go backwards.
    assert len(chunks) >= 2
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(c.text for c in chunks)
    starts = [c.start_time for c in chunks]
    assert starts == sorted(starts)
    assert starts[0] == 0.0


def test_consecutive_chunks_overlap_at_the_seam(monkeypatch):
    # Arrange
    monkeypatch.setattr("ingestion.chunker.MAX_CHUNK_SIZE", 4)
    monkeypatch.setattr("ingestion.chunker.OVERLAP_TOKEN_SIZE", 1)

    # Act
    chunks = chunk_transcript(_make_word_transcript())

    # Assert 1 — nothing was lost: every original word still appears somewhere.
    seen = " ".join(c.text for c in chunks).split()
    assert set(seen) == set(_WORDS)

    # Assert 2 — THE SEAM. Each chunk must OPEN with a non-empty run of words
    # that the previous chunk ENDED with. That shared run is the overlap: the
    # tail of chunk N reappears at the head of chunk N+1.
    assert len(chunks) >= 2
    for prev, nxt in zip(chunks, chunks[1:]):
        prev_words = prev.text.split()
        next_words = nxt.text.split()
        shares_seam = any(
            prev_words[-k:] == next_words[:k] for k in range(1, len(prev_words) + 1)
        )
        assert shares_seam, f"no overlap seam between {prev_words} and {next_words}"
