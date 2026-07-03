from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from collections import defaultdict
import uuid
import time

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
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

# -----------------------
# Rate limit storage
# -----------------------

client_requests = defaultdict(list)

# -----------------------
# Request Context + Rate Limiter
# -----------------------

@app.middleware("http")
async def middleware(request: Request, call_next):
    # Request ID
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    # Skip rate limiting for preflight
    if request.method != "OPTIONS":
        client_id = request.headers.get("X-Client-Id", "anonymous")
        now = time.time()

        # Remove expired requests
        client_requests[client_id] = [
            t for t in client_requests[client_id]
            if now - t < WINDOW
        ]

        if len(client_requests[client_id]) >= RATE_LIMIT:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
            )
            response.headers["X-Request-ID"] = request_id
            return response

        client_requests[client_id].append(now)

    response = await call_next(request)

    # Echo request ID in every response
    response.headers["X-Request-ID"] = request_id

    return response

# -----------------------
# Endpoint
# -----------------------

@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }
