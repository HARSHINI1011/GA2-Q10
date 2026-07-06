"""
Middleware Stack Assignment: Rate-Limit + CORS + Request Context
------------------------------------------------------------------
Run locally with:
    uvicorn main:app --reload

Then test with curl (see README.md for full examples):
    curl -i http://127.0.0.1:8000/ping -H "X-Request-ID: abc-123"
"""

import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

# ============================================================
# 1. CONFIG — fill in your own values here
# ============================================================
YOUR_EMAIL = "you@example.com"  # <-- put YOUR logged-in email here

ALLOWED_ORIGINS = [
    "https://app-yt9och.example.com",  # your assigned CORS origin
    # The instructions say to also allow the exam/grader page's origin
    # so the browser-based grader can call /ping. Replace the line below
    # with the ACTUAL origin the grader page runs on (open the grader
    # page, check its URL bar -> that scheme+host+port is the "origin").
    "https://REPLACE-WITH-EXAM-PAGE-ORIGIN",
]

RATE_LIMIT_MAX = 13          # your assigned bucket size (B)
RATE_LIMIT_WINDOW_SECONDS = 10


# ============================================================
# 2. MIDDLEWARE #1 — Request Context
#    Job: make sure every request/response has a request_id,
#    reusing the client's own X-Request-ID if they sent one.
# ============================================================
class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        incoming_id = request.headers.get("X-Request-ID")
        request_id = incoming_id if incoming_id else str(uuid.uuid4())

        # Stash it on the request so the /ping endpoint can read it later
        request.state.request_id = request_id

        # Let the request continue down the chain (rate limiter -> endpoint)
        response = await call_next(request)

        # Stamp it onto the outgoing response too
        response.headers["X-Request-ID"] = request_id
        return response


# ============================================================
# 3. MIDDLEWARE #2 — Per-client Rate Limiter
#    Job: count requests per X-Client-Id in a rolling 10s window.
#    In-memory storage is fine for an assignment (resets on restart).
# ============================================================
_buckets: dict[str, deque] = defaultdict(deque)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_id = request.headers.get("X-Client-Id", "anonymous")
        now = time.monotonic()
        bucket = _buckets[client_id]

        # Throw away timestamps older than the window (they no longer count)
        while bucket and now - bucket[0] > RATE_LIMIT_WINDOW_SECONDS:
            bucket.popleft()

        if len(bucket) >= RATE_LIMIT_MAX:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
            )

        bucket.append(now)
        return await call_next(request)


# ============================================================
# 4. MIDDLEWARE #3 — CORS
#    Job: only let the allowed origins see the response
#    (no wildcard "*"), and make OPTIONS preflight work.
# ============================================================
# IMPORTANT ORDERING NOTE (read this twice!):
# Starlette/FastAPI run middleware in the REVERSE order you add them —
# the LAST one added becomes the OUTERMOST layer that sees the request
# first and the response last. We want CORS to be outermost, so that
# it can intercept and answer OPTIONS preflight requests immediately,
# before they ever reach the rate limiter or the request-id logic.
# That's why CORSMiddleware is added LAST here, even though
# conceptually it's "Middleware 2" in the assignment description.
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,   # exact origins only, never "*"
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


# ============================================================
# 5. THE ENDPOINT
# ============================================================
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": YOUR_EMAIL,
        "request_id": request.state.request_id,
    }
