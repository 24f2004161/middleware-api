from collections import defaultdict, deque
from math import ceil
from uuid import uuid4
import time

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

EMAIL = "24f2004161@ds.study.iitm.ac.in"

RATE_LIMIT = 12
WINDOW = 10

app = FastAPI()

# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-g8fsm6.example.com",
        "https://exam.sanand.workers.dev",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Retry-After"],
)

# -----------------------------
# Request Context Middleware
# -----------------------------
@app.middleware("http")
async def request_context(request: Request, call_next):

    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


# -----------------------------
# Rate Limiter
# -----------------------------
buckets = defaultdict(deque)


async def rate_limit(request: Request):

    if request.method == "OPTIONS":
        return

    client = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()

    bucket = buckets[client]

    while bucket and now - bucket[0] >= WINDOW:
        bucket.popleft()

    if len(bucket) >= RATE_LIMIT:

        retry = max(
            1,
            ceil(WINDOW - (now - bucket[0]))
        )

        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(retry)
            },
        )

    bucket.append(now)


# -----------------------------
# Exception handler
# -----------------------------
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):

    from fastapi.responses import JSONResponse

    response = JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

    if exc.headers:
        for k, v in exc.headers.items():
            response.headers[k] = v

    response.headers["X-Request-ID"] = request.state.request_id

    return response


# -----------------------------
# Routes
# -----------------------------
@app.get("/")
async def root():
    return {"status": "ok"}


@app.get("/ping", dependencies=[Depends(rate_limit)])
async def ping(request: Request):

    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }
