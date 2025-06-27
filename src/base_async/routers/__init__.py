from .healthcheck import router
from fastapi import APIRouter

api_router = APIRouter()
api_router.include_router(healthcheck.router, prefix='/healthcheck', tags=['Healthcheck'])