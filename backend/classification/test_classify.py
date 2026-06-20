from classification.classify import build_input


def test_short_text_is_included_whole():
    out = build_input("My Title", "short body", sample_chars_size=1500)
    assert "short body" in out


def test_long_text_is_truncated_to_sample_size():
    body = "x" * 5000
    out = build_input("My Title", body, sample_chars_size=1500)
    # only the sample's worth of body should appear, not all 5000 chars
    assert out.count("x") == 1500


def test_both_title_and_sample_are_present():
    out = build_input("Mixolydian Mode Lesson", "play the b7 over the V chord")
    assert "Mixolydian Mode Lesson" in out
    assert "play the b7 over the V chord" in out