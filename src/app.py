from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
import uvicorn

from src.base_async.base_module.exception import exception_handler
from src.injectors.connections import pg
from src.routers import api_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await pg.setup()
    yield


def setup_app() -> FastAPI:
    project_name = os.getenv('PROJECT_NAME', 'Test Task Veysman Refactored')
    project_desc = os.getenv('PROJECT_DESK', 'New refactored version of test task')

    app = FastAPI(
        title=project_name,
        description=project_desc,
        openapi_url='/api/openapi.json',
        docs_url='/docs',
        lifespan=lifespan,
    )

    exception_handler(app)
    app.include_router(api_router, prefix='/api')
    return app


app = setup_app()


def main() -> None:
    uvicorn.run(
        app,
        host=os.getenv('APP_HOST', '0.0.0.0'),
        port=os.getenv('APP_PORT', 8001),
    )


if __name__ == '__main__':
    main()
