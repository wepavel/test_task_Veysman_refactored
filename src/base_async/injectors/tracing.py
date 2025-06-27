import logging
import os
from fastapi import FastAPI, Request
from uuid import uuid4
from ulid import ULID
import time

app = FastAPI()

def setup_tracing(app: FastAPI, logger: logging.Logger) -> None:
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(ULID.from_timestamp(time.time()).to_uuid())
        response = await call_next(request)

        host = request.client.host
        method = request.method
        path = request.url.path
        status = response.status_code

        logger.info(f'{host} {method} {path} {status}')

        response.headers["X-Request-ID"] = req_id
        return response