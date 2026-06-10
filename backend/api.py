import os
import secrets

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from exceptions import LimitExceededError
from middleware import RequestIdMiddleware, SecurityHeadersMiddleware
from models.chat import ChatRequest, ChatResponse
from services import chat_service

logger = structlog.get_logger()

_cors_origins = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
]
_rate_limit = os.getenv("RATE_LIMIT", "20/minute")

limiter = Limiter(key_func=get_remote_address)
_bearer = HTTPBearer()

app = FastAPI(title="Software Engineering Assistant API")
app.state.limiter = limiter
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["POST"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)


def _verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> None:
    api_key = os.getenv("API_KEY", "")
    if api_key and not secrets.compare_digest(credentials.credentials, api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    logger.warning("rate_limit_exceeded", client=get_remote_address(request))
    return JSONResponse(
        status_code=429, content={"detail": "Too many requests. Please slow down."}
    )


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(_verify_api_key)])
@limiter.limit(_rate_limit)
def chat(request: Request, body: ChatRequest):
    try:
        return chat_service.chat(body)
    except LimitExceededError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception:
        logger.error("unhandled_error", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
