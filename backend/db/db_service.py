from models.transcript import Transcript as TranscriptDoc
from db.database import get_engine, Transcript, Status
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
import structlog

logger = structlog.get_logger()


def add_transcripts(rows: list[TranscriptDoc]) -> None:
    if not rows:
        return
    with Session(get_engine()) as session:
        try:
            # this is idempotent, if we just did an add or an isert without .on_conflict_do_nothing
            # and ran the same batch again it would throw an IntegrityError , this just ignores duplicates
            # if in the future i decide i want to update i can just change to .on_conflict_do_update(...)
            session.execute(
                insert(Transcript)
                .values([to_values(row) for row in rows])
                .on_conflict_do_nothing(index_elements=["video_id"])
            )
            session.commit()
        except Exception:
            # this is not necessary, on an exception with saession as session will automatically
            # do a rollback, but it doesnt hurt anything and its explicit
            session.rollback()
            logger.error("add_transcripts failed", exc_info=True)
            raise

def is_transcript_ingested(video_id: str) -> bool:
     with Session(get_engine()) as session:
         stmt = select(Transcript.id).where( Transcript.video_id == video_id, Transcript.status == Status.INGESTED)
         return session.scalars(stmt).first() is not None     

def is_keep(video_id: str) -> bool:
     with Session(get_engine()) as session:
         stmt = select(Transcript.id).where( Transcript.video_id == video_id, Transcript.status == Status.CLASSIFIED_KEEP)
         return session.scalars(stmt).first() is not None
      
def mark_ingested(video_id) -> None:
     with Session(get_engine()) as session:
        try:
            stmt = update(Transcript).where(Transcript.video_id == video_id).values(status=Status.INGESTED)
            session.execute(stmt)
            session.commit()
        except Exception:
            logger.error("mark_ingested failed", exc_info=True)
            raise

def get_scraped() -> list[Transcript]:
    with Session(get_engine()) as session:
        stmt = select(Transcript).where( Transcript.status == Status.SCRAPED)
        return list(session.scalars(stmt).all())
        
def mark_classified(video_id: str, status: Status, reject_reason: str | None = None) -> None:
     with Session(get_engine()) as session:
        try:
            stmt = update(Transcript).where(Transcript.video_id == video_id).values(status=status, reject_reason=reject_reason)
            session.execute(stmt)
            session.commit()
        except Exception:
            logger.error("mark_classified failed", exc_info=True)
            raise

# map the pydantic version of the transcript to the database object TranscriptDoc -> Transcript
def to_values(doc: TranscriptDoc) -> dict:
    return {
        "video_id": doc.video_id,
        "title": doc.title,
        "url": doc.url,
        "status": Status.SCRAPED,
        "instructor": doc.instructor,
        "payload": doc.model_dump(mode="json"),
    }
