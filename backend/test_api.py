import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# conftest.py has already stubbed the heavy imports before this module loads.
from api import app, verify_clerk_user, limiter
from services import chat_service
from services.chat_service import question_counts

client = TestClient(app)
FAKE_CONTEXT = "CTX"

def make_invoke_result(reply: str) -> dict:
    msg = MagicMock()
    msg.content = reply
    return {"messages": [msg]}


@pytest.fixture(autouse=True)
def reset_state():
    """Clear per-conversation question counts between tests."""
    question_counts.clear()
    yield

@pytest.fixture(autouse=True)
def disable_rate_limit():
    limiter.enabled = False
    yield
    limiter.enabled = True

@pytest.fixture(autouse=True)
def bypass_auth():
    # /chat requires a valid Clerk JWT via verify_clerk_user. Override that
    # dependency so the endpoint treats every test request as authenticated —
    # no real token/Clerk client needed. (dependency_overrides is FastAPI's
    # official test seam; production wiring is untouched.)
    app.dependency_overrides[verify_clerk_user] = lambda: "test-user-id"
    app.dependency_overrides[verify_clerk_user] = lambda: "test-user-id"
    yield
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def mock_retriever():
    # chat() calls get_retriever().retrieve(); stub it so no real OpenAI/Pinecone
    # client is built. Default context is fine for every test except the one that
    # asserts the augmented prompt.
    with patch.object(chat_service, "get_retriever") as mock_get:
        mock_get.return_value.retrieve.return_value = (FAKE_CONTEXT, [])
        yield mock_get
# ---------------------------------------------------------------------------
# Happy-path
# ---------------------------------------------------------------------------


@patch.object(chat_service, "agent")
def test_chat_returns_reply(mock_agent):
    mock_agent.invoke.return_value = make_invoke_result("Use a linter.")
    resp = client.post(
        "/chat", json={"conversation_id": "t1", "message": "clean code tips?"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["reply"] == "Use a linter."
    assert body["questions_remaining"] == chat_service.MAX_QUESTIONS - 1


@patch.object(chat_service, "agent")
def test_questions_remaining_decrements(mock_agent):
    mock_agent.invoke.return_value = make_invoke_result("answer")
    conv = "decrement-conv"
    for expected_remaining in range(chat_service.MAX_QUESTIONS - 1, -1, -1):
        resp = client.post("/chat", json={"conversation_id": conv, "message": "q"})
        assert resp.json()["questions_remaining"] == expected_remaining


# ---------------------------------------------------------------------------
# Conversation isolation
# ---------------------------------------------------------------------------


@patch.object(chat_service, "agent")
def test_separate_conversations_tracked_independently(mock_agent):
    mock_agent.invoke.return_value = make_invoke_result("answer")
    r1 = client.post("/chat", json={"conversation_id": "conv-a", "message": "q"})
    r2 = client.post("/chat", json={"conversation_id": "conv-b", "message": "q"})
    assert r1.json()["questions_remaining"] == chat_service.MAX_QUESTIONS - 1
    assert r2.json()["questions_remaining"] == chat_service.MAX_QUESTIONS - 1


# ---------------------------------------------------------------------------
# Rate-limiting
# ---------------------------------------------------------------------------


@patch.object(chat_service, "agent")
def test_question_limit_returns_429(mock_agent):
    mock_agent.invoke.return_value = make_invoke_result("answer")
    conv = "limit-conv"
    for _ in range(chat_service.MAX_QUESTIONS):
        client.post("/chat", json={"conversation_id": conv, "message": "q"})
    resp = client.post("/chat", json={"conversation_id": conv, "message": "one more"})
    assert resp.status_code == 429


@patch.object(chat_service, "agent")
def test_question_limit_does_not_affect_other_conversations(mock_agent):
    mock_agent.invoke.return_value = make_invoke_result("answer")
    exhausted = "exhausted-conv"
    fresh = "fresh-conv"
    for _ in range(chat_service.MAX_QUESTIONS):
        client.post("/chat", json={"conversation_id": exhausted, "message": "q"})
    resp = client.post("/chat", json={"conversation_id": fresh, "message": "q"})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Agent invocation contract
# ---------------------------------------------------------------------------


@patch.object(chat_service, "agent")
def test_agent_called_with_correct_thread_id(mock_agent):
    mock_agent.invoke.return_value = make_invoke_result("answer")
    client.post(
        "/chat", json={"conversation_id": "my-thread", "message": "how to use arepeggios?"}
    )
    augmented = f"Context from guitar transcripts:\n\n{FAKE_CONTEXT}\n\nQuestion: how to use arepeggios?"
    mock_agent.invoke.assert_called_once_with(
        {"messages": [{"role": "user", "content": augmented}]},
        config={"configurable": {"thread_id": "my-thread"}},
    )


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@patch.object(chat_service, "agent")
def test_agent_exception_returns_500(mock_agent):
    mock_agent.invoke.side_effect = Exception("model blew up")
    resp = client.post("/chat", json={"conversation_id": "err-conv", "message": "q"})
    assert resp.status_code == 500


@patch.object(chat_service, "agent")
def test_failed_call_does_not_increment_count(mock_agent):
    mock_agent.invoke.side_effect = Exception("fail")
    conv = "fail-conv"
    client.post("/chat", json={"conversation_id": conv, "message": "q"})
    assert question_counts.get(conv, 0) == 0
