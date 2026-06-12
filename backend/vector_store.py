from dataclasses import dataclass
from typing import Protocol, Any
import os
from dotenv import load_dotenv
from models.query import QueryResponse

load_dotenv()

@dataclass
class VectorRecord:
    id: str
    vector: list[float]
    metadata: dict
    

class VectorStore(Protocol):
    def upsert(self, records: list[VectorRecord], namespace=""): ...
    def query(self, vector: list[float], top_k: int = 5, namespace="") -> QueryResponse: ...

class PineconeVectorStore:
    def __init__(self) -> None:
        from pinecone import Pinecone
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "guitar-rag")
        #this constructor gets the PINECONE_API_KEY from envireonment
        self.pc = Pinecone()
        self.index = self.pc.Index(self.index_name)
        

    def upsert(self, records: list[VectorRecord], namespace="") -> None:               
        pinecone_data: list[dict] = self.to_pinecone(records)
        try:
            self.index.upsert(namespace=namespace, vectors=pinecone_data)                        
        except Exception as e:
            # Handle other errors
            print(f"Unexpected error: {e}")
            raise 
                    
        
    
    def query(self, vector: list[float], top_k: int = 5, namespace="")  -> QueryResponse:        
        try:
            raw_response = self.index.query(
                namespace=namespace,
                vector=vector, 
                top_k=top_k,
                include_metadata=True,
                include_values=False 
            )

            query_response: QueryResponse = QueryResponse(**raw_response.to_dict())            
            return query_response                      
        except Exception as e:
            # Handle other errors
            print(f"Unexpected error: {e}")
            raise 
        
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
