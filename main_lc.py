from langchain.agents import create_agent
from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from dotenv import load_dotenv

load_dotenv()

MAX_QUESTIONS = 10

SYSTEM_PROMPT = """You are a helpful assistant that answers questions about the sofware engineering.
                   You have access to a large amount of information and can provide
                   detailed and accurate answers to any question. You are also able to
                   provide sources for your answers when possible. Only allow questions related to programming or sofware engineering,
                   otherwise respond with "That question is not relevant to software engineering.".
                   """

llm = ChatAnthropic(model="claude-haiku-4-5-20251001", max_tokens=1024)
agent = create_agent(
    model=llm,
    system_prompt=SYSTEM_PROMPT,
    checkpointer=MemorySaver(),
)

THREAD_CONFIG = {"configurable": {"thread_id": "conversation-1"}}


def conversation():
    question_count = 0

    while True:
        human_prompt = input("You? ").strip()
        if human_prompt.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        if question_count >= MAX_QUESTIONS:
            print("\nMaximum number of questions per conversation reached")
            print("Goodbye!")
            break

        question_count += 1

        try:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": human_prompt}]},
                config=THREAD_CONFIG,
            )
            reply = result["messages"][-1].content
            print("Answer:")
            print(reply)
            print("\n\n")
        except Exception as e:
            print(e)


if __name__ == "__main__":
    conversation()
