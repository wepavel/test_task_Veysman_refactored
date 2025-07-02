from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import uvicorn

from src.base_async.base_module import http_exception_handler, starlette_exception_handler, validation_exception_handler
from src.injectors.connections import pg
from src.routers import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await pg.setup()
    yield


def setup_app() -> FastAPI:
    project_name = 'Test Task Veysman Refactored'
    project_desc = 'New refactored version of test task'

    app = FastAPI(
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None
    )

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, starlette_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    app.include_router(api_router, prefix='/api')

    return app


app = setup_app()


def main() -> None:
    uvicorn.run(
        app,
        host='0.0.0.0',
        port=8001,
    )


if __name__ == '__main__':
    main()
