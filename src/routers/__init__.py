from fastapi import APIRouter

from .file import router  # noqa: F401

api_router = APIRouter()
api_router.include_router(file.router, tags=['Files'])
