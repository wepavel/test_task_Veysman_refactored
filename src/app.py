from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.base_async.base_module import get_logger, setup_logging
from src.base_async.base_module.exception import exception_handler
from src.base_async.injectors.openapi import custom_openapi
from src.base_async.middleware.tracing import setup_tracing
from src.base_async.routers import api_router as base_router
from src.injectors.connections import pg
from src.routers import api_router as main_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(log_level='DEBUG')
    await pg.setup()
    yield


def setup_app() -> FastAPI:
    project_name = os.getenv('PROJECT_NAME', 'Default Project Name')
    project_desc = os.getenv('PROJECT_DESK', 'Default Description')

    app = FastAPI(
        title=project_name,
        lifespan=lifespan,
        openapi_url='/api/openapi.json',
        docs_url='/docs',
    )
    setup_tracing(app=app, logger=get_logger())

    custom_openapi(app, project_name, project_desc)
    exception_handler(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    app.include_router(base_router, prefix='/api')
    app.include_router(main_router, prefix='/api')

    return app


app = setup_app()


def main() -> None:
    uvicorn.run(
        app,
        host=os.getenv('APP_HOST', '0.0.0.0'),
        port=os.getenv('APP_PORT', 8023),
        log_config='log_config.json',
        access_log=False,
    )


if __name__ == '__main__':
    main()
