from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import defaultdict, deque
from uuid import uuid4
from math import ceil
import time

EMAIL = "24f2004161@ds.study.iitm.ac.in"

RATE_LIMIT = 120
WINDOW = 10

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app-g8fsm6.example.com",
        "https://exam.sanand.workers.dev",   # replace if your exam uses another origin
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "Retry-After"],
)

# client_id -> timestamps
buckets = defaultdict(deque)


@app.middleware("http")
async def request_context_and_rate_limit(request: Request, call_next):

    # ----------------------------
    # Request ID
    # ----------------------------
    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid4())

    request.state.request_id = request_id

    # ----------------------------
    # Skip OPTIONS
    # ----------------------------
    if request.method != "OPTIONS":

        client = request.headers.get(
            "X-Client-Id",
            "anonymous"
        )

        now = time.time()

        bucket = buckets[client]

        while bucket and now - bucket[0] >= WINDOW:
            bucket.popleft()

        if len(bucket) >= RATE_LIMIT:

            retry_after = max(
                1,
                ceil(WINDOW - (now - bucket[0]))
            )

            response = JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded"
                }
            )

            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-Request-ID"] = request_id

            return response

        bucket.append(now)

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


@app.get("/ping")
async def ping(request: Request):

    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }
