import structlog

from agent import agent, MAX_QUESTIONS
from exceptions import LimitExceededError
from models.chat import ChatRequest, ChatResponse
from rag.retriever import Retriever

logger = structlog.get_logger()

question_counts: dict[str, int] = {}
retriever = Retriever()

def chat(request: ChatRequest) -> ChatResponse:
    count = question_counts.get(request.conversation_id, 0)
    if count >= MAX_QUESTIONS:
        raise LimitExceededError("max number of questions reached")
    
    try:
        # first get the relevent data from the vector stor
       
        text, sources = retriever.retrieve( request.message )

        #augmented is the context data from the vector db AND the question for the llm
        augmented = f"Context from guitar transcripts:\n\n{text}\n\nQuestion: {request.message}"


        #call the agent
        response = agent.invoke(
            {"messages": [{"role": "user", "content": augmented}]},
            config={"configurable": {"thread_id": request.conversation_id}},
        )
        reply_message = response["messages"][-1].content
        question_counts[request.conversation_id] = count + 1
        return ChatResponse(
            reply=reply_message,
            questions_remaining=MAX_QUESTIONS
            - question_counts[request.conversation_id],
            sources=sources
        )
    except LimitExceededError:
        raise
    except Exception:
        logger.error("agent_invocation_failed", exc_info=True)
        raise
