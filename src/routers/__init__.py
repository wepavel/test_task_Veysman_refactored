from fastapi import APIRouter

from .file_info import router
from .file_manager import router  # noqa: F401

api_router = APIRouter()
api_router.include_router(file_manager.router, prefix='/file-manager', tags=['File manager'])
api_router.include_router(file_info.router, prefix='/file-info', tags=['File info'])
