from pathlib import Path
import json
import structlog
from models.transcript import Transcript
from ingestion.chunker import chunk_transcript, filter_transcript
from embeddings.embeddings import get_embedding_provider, EmbeddingProvider
from vector_store import VectorRecord, VectorStore, get_vector_store_provider
from db.db_service import is_keep, mark_ingested


logger = structlog.get_logger()


    

def load_data_filelist() -> list[Path]:
    target_dir = Path(__file__).resolve().parents[2] / "data_gathering/transcripts/"
    files = [f for f in Path(target_dir).rglob("*.json") if f.is_file()]

    return files


def load_transcript(path: Path) -> Transcript:
    with open(path, "r", encoding="utf-8") as file:
        return Transcript.model_validate(json.load(file))
    

    

def run_ingest():
    logger.info('beginning embedding run')
    file_list = load_data_filelist()
    logger.info(f"have {len(file_list)} transcripts to process")
    embedding_provider: EmbeddingProvider = get_embedding_provider()
    vector_store_provider: VectorStore = get_vector_store_provider()
    total_messagees = 0
    total_transcripts_processed = 0
    for path in file_list:
        try:
            transcript = load_transcript(path)

            if not is_keep(transcript.video_id):
                logger.info(f"skipping {transcript.video_id} — not in CLASSIFIED_KEEP")
                continue

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
                        "instructor": chunk.instructor.title(),
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
            
            mark_ingested(transcript.video_id) 
            total_transcripts_processed += 1
        except Exception as e:
            logger.info(str(e))

    logger.info(f"senting {total_messagees} to vector database")
    logger.info(f"completed embedding run with {total_transcripts_processed} transcripts processed")


if __name__ == "__main__":
    run_ingest()
