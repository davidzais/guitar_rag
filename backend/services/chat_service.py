import structlog

from agent import agent, MAX_QUESTIONS
from exceptions import LimitExceededError
from models.chat import ChatRequest, ChatResponse

logger = structlog.get_logger()

question_counts: dict[str, int] = {}


def chat(request: ChatRequest) -> ChatResponse:
    count = question_counts.get(request.conversation_id, 0)
    if count >= MAX_QUESTIONS:
        raise LimitExceededError("max number of questions reached")

    thread_config = {"configurable": {"thread_id": request.conversation_id}}

    try:
        response = agent.invoke(
            {"messages": [{"role": "user", "content": request.message}]},
            config=thread_config,
        )
        reply_message = response["messages"][-1].content
        question_counts[request.conversation_id] = count + 1
        return ChatResponse(
            reply=reply_message,
            questions_remaining=MAX_QUESTIONS - question_counts[request.conversation_id],
        )
    except LimitExceededError:
        raise
    except Exception:
        logger.error("agent_invocation_failed", exc_info=True)
        raise
