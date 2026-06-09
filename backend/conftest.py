import logging
import sys
from unittest.mock import MagicMock

import structlog

# Stub out heavy/external dependencies before any test file imports agent.py or api.py.
# This prevents real network calls or API key requirements during the test run.
for _mod in [
    "dotenv",
    "langchain_anthropic",
    "langchain",
    "langchain.agents",
    "langgraph",
    "langgraph.checkpoint",
    "langgraph.checkpoint.memory",
]:
    sys.modules.setdefault(_mod, MagicMock())

# Configure structlog for tests: readable console output, errors only to reduce noise.
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.ERROR),
    cache_logger_on_first_use=False,
)
