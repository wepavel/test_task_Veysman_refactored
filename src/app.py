import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from src.api import api_router
# from src.core.config import settings
# from src.core.exceptions import exception_handler
# from src.core.logging import logger
# from src.core.openapi import custom_openapi
# from src.file_management.file_watcher import FileWatcher
from injectors import middleware
# from injectors.connections import pg
# from base_async import
from base_async.injectors.openapi import custom_openapi
from injectors.connections import pg
from contextlib import asynccontextmanager

from base_async.routers import router as base_router
from base_async.base_module import get_logger, setup_logging
from src.base_async.injectors.tracing import setup_tracing
# from models import File # noqa


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(log_level='DEBUG')

    await pg.setup()
    yield

def setup_app() -> FastAPI:
    project_name = os.getenv('PROJECT_NAME', 'Default Project Name')
    project_desc = os.getenv('PROJECT_DESK', 'Default Description')

    print(os.listdir(os.getcwd()))
    app = FastAPI(
        title=project_name,
        lifespan=lifespan,
        openapi_url=f'/api/openapi.json',
        docs_url='/docs',
    )
    setup_tracing(app=app, logger=get_logger())

    custom_openapi(app, project_name, project_desc)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    app.include_router(base_router, prefix='/api')

    return app

app = setup_app()
logger = get_logger()

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