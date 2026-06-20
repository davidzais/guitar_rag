import pytest

from classification.policy import should_keep, MIN_CONFIDENCE
from models.classification import Classification, Category


def make(category: Category, confidence: float = 0.9) -> Classification:
    return Classification(category=category, confidence=confidence, reason="t")


def test_keeps_high_confidence_instruction():
    assert should_keep(make(Category.INSTRUCTION, 0.9)) is True


def test_rejects_instruction_below_threshold():
    assert should_keep(make(Category.INSTRUCTION, 0.5)) is False


@pytest.mark.parametrize(
    "category",
    [
        Category.SONG_TUTORIAL,
        Category.PERFORMANCE,
        Category.PRODUCT_DEMO,
        Category.OTHER,
    ],
)
def test_rejects_non_instruction_even_if_confident(category):
    assert should_keep(make(category, 0.99)) is False


def test_keeps_at_exact_threshold():
    # pins the boundary: >= MIN_CONFIDENCE, not >
    assert should_keep(make(Category.INSTRUCTION, MIN_CONFIDENCE)) is True