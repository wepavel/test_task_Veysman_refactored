import asyncio
import os

from fastapi import FastAPI
import uvicorn

from src.base_async.base_module.exception import exception_handler
from src.base_async.injectors.openapi import custom_openapi
from src.injectors.connections import pg
from src.routers import api_router


def setup_app() -> FastAPI:
    asyncio.run(pg.setup())

    project_name = os.getenv('PROJECT_NAME', 'Test Task Veysman Refactored')
    project_desc = os.getenv('PROJECT_DESK', 'New refactored version of test task')

    app = FastAPI(
        title=project_name,
        openapi_url='/api/openapi.json',
        docs_url='/docs',
    )
    custom_openapi(app, project_name, project_desc)
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
