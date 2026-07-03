from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uuid
import time
from collections import defaultdict

EMAIL = "24f2004161@ds.study.iitm.ac.in"

ALLOWED_ORIGINS = [
    "https://app-g8fsm6.example.com",
    "https://exam.sanand.workers.dev",
]

RATE_LIMIT = 12
WINDOW = 10  # seconds

app = FastAPI()

# -----------------------
# CORS
# -----------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

# -----------------------
# Rate limit storage
# -----------------------

client_buckets = defaultdict(list)

# -----------------------
# Request Context Middleware
# -----------------------

@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    # Always echo request id in response header
    response.headers["X-Request-ID"] = request_id

    return response

# -----------------------
# Rate Limiter Middleware
# -----------------------

@app.middleware("http")
async def rate_limiter(request: Request, call_next):

    # Don't rate limit CORS preflight
    if request.method == "OPTIONS":
        return await call_next(request)

    client_id = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()

    bucket = client_buckets[client_id]

    # Remove expired timestamps
    while bucket and now - bucket[0] >= WINDOW:
        bucket.pop(0)

    if len(bucket) >= RATE_LIMIT:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )

        # Echo request id even on errors
        response.headers["X-Request-ID"] = request.state.request_id

        return response

    bucket.append(now)

    return await call_next(request)

# -----------------------
# Endpoint
# -----------------------

@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }
