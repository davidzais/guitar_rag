from dataclasses import dataclass
from typing import Protocol, Any
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass
class VectorRecord:
    id: str
    vector: list[float]
    metadata: dict
    

class VectorStore(Protocol):
    def upsert(self, records: list[VectorRecord]): ...
    def query(self, vector: list[float], top_k: int = 5): ...

class PineconeVectorStore:
    def __init__(self):
        from pinecone import Pinecone
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "guitar-rag")
        #this constructor gets the PINECONE_API_KEY from envireonment
        self.pc = Pinecone()
        self.index = self.pc.Index(self.index_name)
        

    def upsert(self, records: list[VectorRecord]) -> None: 
        from pinecone import PineconeException
        
        pinecone_data: list[dict] = self.to_pinecone(records)
        try:
            self.index.upsert(namespace="", vectors=pinecone_data)         
        except PineconeException as e:
            # Handle Pinecone-specific errors
            print(f"Pinecone error: {e}")
            raise Exception(e)            
        except Exception as e:
            # Handle other errors
            print(f"Unexpected error: {e}")
            raise Exception(e)
                    
        
    
    def query(self, vector: list[float], top_k: int = 5) -> None: ... 

    def to_pinecone(self, records: list[VectorRecord]) -> list[dict]:
        mapped_data: list[dict] = []
        for rec in records:
            data: dict[str, Any] = {}
            data["id"] = rec.id
            data["values"] = rec.vector                     
            data["metadata"] = {k: v for k, v in rec.metadata.items() if v is not None}

            mapped_data.append(data)
            
        return mapped_data
    

def get_vector_store_provider() -> VectorStore:
    
    vector_store_provider = os.getenv("VECTOR_STORE_PROVIDER", "pinecone")
    # right now this is only returning pinecone, but just showing that there is the potential for different vector store providers
    match vector_store_provider:
        case "pinecone":
            return PineconeVectorStore()
        case _:
            raise ValueError(f"Unknown vector store provider: {vector_store_provider!r}")
