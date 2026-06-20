from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from functools import cache
from youtube.data_models import Transcript

load_dotenv()


def video_id_exists(video_id: str) -> bool:
    with get_engine().connect() as conn:
        return conn.execute(
            text("SELECT 1 FROM transcript WHERE video_id = :v"), {"v": video_id}
        ).first() is not None


def add_transcript(transcript: Transcript) -> None:
    stmt = text("""INSERT INTO transcript (video_id, instructor, title, url, payload, status)
      VALUES (:vid, :instr, :title, :url, CAST(:payload AS jsonb), 'SCRAPED')
      ON CONFLICT (video_id) DO NOTHING""")

    with get_engine().begin() as conn:
        conn.execute(stmt, {
        "vid": transcript.video_id,
        "instr": transcript.instructor,
        "title": transcript.title,
        "url": transcript.url,
        "payload": transcript.model_dump_json(),
    })


@cache
def get_engine():
    return create_engine(os.environ["DATABASE_URL"])