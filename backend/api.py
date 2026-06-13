import os
import structlog
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from exceptions import LimitExceededError
from middleware import RequestIdMiddleware, SecurityHeadersMiddleware
from models.chat import ChatRequest, ChatResponse
from services import chat_service
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions

from fastapi.security import HTTPBearer   

bearer_scheme = HTTPBearer(auto_error=False)   

logger = structlog.get_logger()

_cors_origins = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
]
_rate_limit = os.getenv("RATE_LIMIT", "20/minute")

limiter = Limiter(key_func=get_remote_address)
clerk = Clerk(bearer_auth=os.environ["CLERK_SECRET_KEY"])

app = FastAPI(title="Guitar Tutor API")
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



def verify_clerk_user(request: Request,  _credentials=Depends(bearer_scheme)) -> str:
    state = clerk.authenticate_request(request, 
                                       AuthenticateRequestOptions(authorized_parties=_cors_origins))
    payload = state.payload
    if not state.is_signed_in or payload is None:
        raise HTTPException(401, "Not authenticated")
    return payload["sub"]   # the Clerk user id

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    logger.warning("rate_limit_exceeded", client=get_remote_address(request))
    return JSONResponse(
        status_code=429, content={"detail": "Too many requests. Please slow down."}
    )


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_clerk_user)])
@limiter.limit(_rate_limit)
def chat(request: Request, body: ChatRequest):
    try:
        return chat_service.chat(body)
    except LimitExceededError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception:
        logger.error("unhandled_error", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
