from fastapi import APIRouter
from .file_manager import router

api_router = APIRouter()
api_router.include_router(file_manager.router, prefix='/file-manager', tags=['File manager'])