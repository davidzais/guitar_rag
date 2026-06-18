from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from functools import cache

load_dotenv()


def video_id_exists(video_id: str) -> bool:
    with get_engine().connect() as conn:
        return conn.execute(
            text("SELECT 1 FROM transcript WHERE video_id = :v"), {"v": video_id}
        ).first() is not None

@cache
def get_engine():
    return create_engine(os.environ["DATABASE_URL"])