"""Tests for the embedding provider.

Run from the backend/ directory:
    python -m pytest embeddings/test_embeddings.py -v

There are three kinds of test here:
  1. Factory  — does get_embedding_provider() return the right class?
  2. Unit     — does our unpacking logic pull the vectors out correctly?
                (the OpenAI network call is FAKED, so no key/network needed)
  3. Integration — does the REAL OpenAI API behave as we assume?
                (skipped automatically unless OPENAI_API_KEY is set)
"""

import os
from unittest.mock import MagicMock

import pytest

from embeddings.embeddings import get_embedding_provider, OpenAIEmbeddingProvider


# ---------------------------------------------------------------------------
# Fixture: a provider whose OpenAI client is FAKE.
#
# Problem: OpenAIEmbeddingProvider.__init__ calls `OpenAI()`, which demands a
# real API key the moment the object is built. We don't want that in a unit
# test. So we replace the `OpenAI` class itself with a MagicMock BEFORE we
# construct the provider. Now `OpenAI()` returns a fake object instead of a
# real client — no key, no network.
#
# `monkeypatch` is a built-in pytest fixture; naming it as a parameter is all
# you need to get it. It undoes every change automatically when the test ends.
# ---------------------------------------------------------------------------
@pytest.fixture
def provider(monkeypatch):
    # Replace openai.OpenAI with a fake. __init__ does `from openai import OpenAI`
    # at call time, so it will pick up this fake instead of the real class.
    monkeypatch.setattr("openai.OpenAI", MagicMock())
    return OpenAIEmbeddingProvider()


# ---------------------------------------------------------------------------
# 1. Factory test — routing only. No real client is built (we fake OpenAI),
#    so this needs no API key.
# ---------------------------------------------------------------------------
def test_factory_returns_openai_provider(monkeypatch):
    monkeypatch.setattr("openai.OpenAI", MagicMock())  # construction needs no key
    monkeypatch.setenv("EMBEDDING_PROVIDER", "openai")  # force the "openai" branch
    provider = get_embedding_provider()
    assert isinstance(provider, OpenAIEmbeddingProvider)


def test_factory_rejects_unknown_provider(monkeypatch):
    # An unknown name should fail LOUDLY, not return None.
    monkeypatch.setenv("EMBEDDING_PROVIDER", "does_not_exist")
    with pytest.raises(ValueError):
        get_embedding_provider()


# ---------------------------------------------------------------------------
# 2. Unit tests — prove OUR unpacking logic, with a faked network response.
#
# The real OpenAI response looks like:
#     response.data == [ item0, item1, ... ]   # one item per input string
#     item.embedding == [float, float, ...]    # that item's vector
#
# We hand-build a fake response with that exact shape, tell the fake client to
# return it, then check our code pulls the vectors out correctly.
# ---------------------------------------------------------------------------
def test_embed_documents_unpacks_each_embedding(provider):
    # Arrange: fake response with TWO items (two input strings -> two vectors).
    # MagicMock(embedding=[...]) makes an object whose `.embedding` is that list.
    provider.client.embeddings.create.return_value.data = [
        MagicMock(embedding=[0.1, 0.2, 0.3]),
        MagicMock(embedding=[0.4, 0.5, 0.6]),
    ]

    # Act
    result = provider.embed_documents(["hello", "world"])

    # Assert: a LIST of vectors, in order.
    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]


def test_embed_query_returns_single_vector(provider):
    # Arrange: a query is ONE string, so the response has ONE item.
    provider.client.embeddings.create.return_value.data = [
        MagicMock(embedding=[0.7, 0.8, 0.9]),
    ]

    # Act
    result = provider.embed_query("G major chord")

    # Assert: ONE flat vector (list[float]), NOT a list-of-lists. This is the
    # exact difference between embed_query and embed_documents.
    assert result == [0.7, 0.8, 0.9]


# ---------------------------------------------------------------------------
# 3. Integration test — the REAL API. Skipped unless OPENAI_API_KEY is set,
#    so the suite stays green without credentials. Run it occasionally to
#    confirm OpenAI still returns what we assume (1536 floats).
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="needs a real OPENAI_API_KEY — integration test",
)
def test_embed_query_real_api_returns_1536_floats():
    provider = OpenAIEmbeddingProvider()
    vec = provider.embed_query("G major chord shape")
    assert len(vec) == 1536
    assert all(isinstance(x, float) for x in vec)
