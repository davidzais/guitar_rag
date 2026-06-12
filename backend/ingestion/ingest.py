from pathlib import Path
import json
from models.transcript import Transcript
from ingestion.chunker import chunk_transcript, filter_transcript
from embeddings.embeddings import get_embedding_provider, EmbeddingProvider
from vector_store import VectorRecord, VectorStore, get_vector_store_provider



    

def load_data_filelist() -> list[Path]:
    target_dir = Path(__file__).resolve().parents[2] / "data_gathering/transcripts/"
    files = [f for f in Path(target_dir).rglob("*") if f.is_file()]

    return files


def load_transcript(path: Path) -> Transcript:
    with open(path, "r", encoding="utf-8") as file:
        return Transcript.model_validate(json.load(file))
    

    

def main():
    print('beginning embedding run')
    file_list = load_data_filelist()
    print(f"have {len(file_list)} transcripts to process")
    embedding_provider: EmbeddingProvider = get_embedding_provider()
    vector_store_provider: VectorStore = get_vector_store_provider()
    total_messagees = 0
    for path in file_list:
        try:
            transcript = load_transcript(path)
            transcript.segments = filter_transcript(transcript.segments)
            chunks = chunk_transcript(transcript)
            chunk_list = [chunks[i:i +100] for i in  range(0, len(chunks), 100)]                          
            for batch in chunk_list:
                texts = [c.text for c in batch]
                embedding_list: list[list[float]] = embedding_provider.embed_documents(texts)

                records = [
                
                    VectorRecord(
                        id = f"{chunk.instructor}__{chunk.video_id}__{chunk.chunk_index}",
                        vector=vec,
                        metadata={
                        "text": chunk.text,
                        "instructor": chunk.instructor,
                        "video_id": chunk.video_id,
                        "title": chunk.title,
                        "url": chunk.url,
                        "start_time": chunk.start_time,
                        "chunk_index": chunk.chunk_index,
                        }
                    )                                   
                    for chunk, vec in zip(batch, embedding_list)               
                ]                                
                vector_store_provider.upsert( records) 
                total_messagees += len(records)                    
            
        except Exception as e:
            print(str(e))

    print(f"sendsenting {total_messagees} to vector database")
    print('completed embedding run')


if __name__ == "__main__":
    main()
