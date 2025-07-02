from fastapi import APIRouter

from .files import router  # noqa: F401

api_router = APIRouter()
api_router.include_router(files.router, tags=['Files'])
