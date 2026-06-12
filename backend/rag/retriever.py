from embeddings.embeddings import get_embedding_provider, EmbeddingProvider
from vector_store import VectorStore, get_vector_store_provider
from models.query import QueryResponse
from models.source import Source

class Retriever:
    def __init__ (self) -> None:
        self.embedding_provider: EmbeddingProvider = get_embedding_provider()  
        self.vector_store_provider: VectorStore = get_vector_store_provider()

    def retrieve(self, query: str, top_k: int = 5) -> tuple[str, list[Source]]:    
        try:
            embedded_query = self.embedding_provider.embed_query(query)
            response: QueryResponse = self.vector_store_provider.query(embedded_query, top_k)

            #now that we have the response back from the vector store,lets format it into what the chat service needs
            context = "\n\n".join(m.metadata.text for m in response.matches) 
            sources = [
                Source(
                    title= m.metadata.title,
                    url=m.metadata.url,
                    instructor=m.metadata.instructor,
                    start_time=m.metadata.start_time,
                    snippet=m.metadata.text
                ) 
                for m in response.matches
            ]       
            return context, sources
        except Exception as e:
            raise Exception(e)
        

    

if __name__ == "__main__":
    query: str = "what would jack ruch say about chord construction"
    retriever = Retriever()
    text, sources = retriever.retrieve( query )
    for s in sources:
        print(s,"\n\n") 



    