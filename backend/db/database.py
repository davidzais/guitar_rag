from datetime import datetime
from sqlalchemy import func, create_engine, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from functools import cache
from dotenv import load_dotenv
import os
from enum import Enum

load_dotenv()




class Status(Enum):
    UNKNOWN = "UNKNOWN"
    SCRAPED = "SCRAPED"
    INGESTED = "INGESTED"
    FAILED = "FAILED"
    CLASSIFIED_KEEP = "CLASSIFIED_KEEP"
    CLASSIFIED_REJECT = "CLASSIFIED_REJECT"
# this seems redundant here, but it acutally serves a purpose. Every class that
# inherits from DeclarativeBase creates its own private Registry and metadata
# this forces all classes to share one registry. That way calling Base.metada.create_all
# knows about all the tables because they share the same registry. that wouldnt be the case 
# if each class directly inherited from DeclarativeBase
class Base(DeclarativeBase):
    pass


class Transcript(Base):
    __tablename__ = "transcript"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[str] = mapped_column(unique=True)
    instructor: Mapped[str]
    title: Mapped[str]
    url: Mapped[str]
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(default=Status.UNKNOWN)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reject_reason: Mapped[str | None] = mapped_column(default=None)


def init_db():
    #Base.metadata.drop_all(get_engine())   # dev only — wipes the table
    Base.metadata.create_all(get_engine())


@cache
def get_engine():
    return create_engine(os.environ["DATABASE_URL"])

if __name__ == "__main__":
    init_db()

