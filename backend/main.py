import os

from logging_config import configure_logging

configure_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    json_logs=os.getenv("JSON_LOGS", "true").lower() == "true",
)

import uvicorn  # noqa: E402
from api import app  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        log_config=None,
    )
