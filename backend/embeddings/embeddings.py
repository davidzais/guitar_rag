from typing import Protocol
import os
from dotenv import load_dotenv

load_dotenv()


class EmbeddingProvider(Protocol):
    def embed_documents(self, text: list[str]) -> list[list[float]]: ...
    def embed_query(self, query: str) -> list[float]: ...


class OpenAIEmbeddingProvider:
    dimension = 1536  # text-embedding-3-small

    def __init__(self, model: str = "text-embedding-3-small"):
        from openai import OpenAI

        client = OpenAI()
        self.client = client
        self.model = model

    def embed_documents(self, text: list[str]):
        response = self.client.embeddings.create(input=text, model=self.model)
        embeddings = [data.embedding for data in response.data]

        return embeddings

    def embed_query(self, query: str):
        response = self.client.embeddings.create(input=query, model=self.model)
        embeddings = response.data[0].embedding
        return embeddings


def get_embedding_provider() -> EmbeddingProvider:
    provider = os.getenv("EMBEDDING_PROVIDER", "openai")
    # right now this is only returning openai, but just showing that there is the potential for different providers
    match provider:
        case "openai":
            return OpenAIEmbeddingProvider()
        case _:
            raise ValueError(f"Unknown embedding provider: {provider!r}")
