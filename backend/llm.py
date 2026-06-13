from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama
from langchain_core.language_models import BaseChatModel
from dotenv import load_dotenv
import os

load_dotenv()

def get_llm() -> BaseChatModel:
    provider = os.getenv("LLM_PROVIDER", "ollama")
    match provider:
        case "ollama":
            return ChatOllama(model=os.getenv("OLLAMA_BASE_MODEL", "llama3.1:8b"),
                              base_url=os.getenv( "OLLAMA_BASE_URL", "http://localhost:11434"),
                             )
        case "anthropic":
            return ChatAnthropic(model="claude-haiku-4-5-20251001", max_tokens=1024)
        case _:
            raise ValueError(f"Unknown LLM Provider: {provider}")