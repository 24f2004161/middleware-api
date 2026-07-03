from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

import uuid
import time
from collections import defaultdict

EMAIL = "24f2004161@ds.study.iitm.ac.in"

ALLOWED_ORIGINS = [
    "https://app-g8fsm6.example.com",

    "https://exam.sanand.workers.dev"
]

RATE_LIMIT = 12
WINDOW = 10

app = FastAPI()

# -----------------------
# CORS
# -----------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# Request Context
# -----------------------

class RequestContextMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id

        response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        return response


app.add_middleware(RequestContextMiddleware)

# -----------------------
# Rate Limiter
# -----------------------

requests = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):

        client = request.headers.get("X-Client-Id", "anonymous")

        now = time.time()

        requests[client] = [
            t for t in requests[client]
            if now - t < WINDOW
        ]

        if len(requests[client]) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
            )

        requests[client].append(now)

        return await call_next(request)


app.add_middleware(RateLimitMiddleware)

# -----------------------
# Endpoint
# -----------------------

@app.get("/ping")
async def ping(request: Request):

    return {
        "email": EMAIL,
        "request_id": request.state.request_id
    }
