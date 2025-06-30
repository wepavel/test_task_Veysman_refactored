from fastapi import APIRouter

from .healthcheck import router  # noqa: F401

api_router = APIRouter()
api_router.include_router(healthcheck.router, prefix='/healthcheck', tags=['Healthcheck'])
