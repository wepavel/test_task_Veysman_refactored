import asyncio
import os
import shutil
from collections.abc import AsyncGenerator
from pathlib import Path

import aiofiles
from fastapi import APIRouter
from fastapi import Depends
from fastapi import File as FastapiFile
from fastapi import UploadFile
from fastapi.responses import StreamingResponse
from sqlmodel.ext.asyncio.session import AsyncSession

# from src import crud
# from src.core.config import settings
# from src.core.exceptions import EXC
# from src.core.exceptions import ErrorCode
# from src.core.file_locker import FileLockMode
# from src.core.file_locker import file_lock_manager
# from src.core.utils import secure_path_join
# from src.models import File
# from src.models import FileCreate
# from src.models import FilePublic
# from src.models import FileUpdate

from src.injectors.connections import pg

CHUNK_SIZE = 1024 * 1024 * 5  # 5 MB
FILE_MAX_SIZE = 100 * 1024 * 1024  # 100 MB

CHECK_FILE_DELAY = 0.5
MAX_RETRIES = 10



def get_file_parts(file_path: str) -> tuple[str, str, str]:
    path_obj = Path(file_path)
    base_name = path_obj.stem
    extension = path_obj.suffix
    directory = str(path_obj.parent)
    return base_name, extension, directory


async def move_file_async(old_path: str, new_path: str) -> str:
    await asyncio.to_thread(shutil.move, old_path, new_path)
    return new_path


router = APIRouter()


@router.post('/upload-file/{file_path:path}')
async def upload_file(
    *,
    db: AsyncSession = Depends(pg.get_session),
    file_path: str,
    input_file: UploadFile = FastapiFile(..., max_size=FILE_MAX_SIZE),
) -> FilePublic:
    """Endpoint for adding file to datastorage.
    If you want to save fie in root dir - use ".", "/" or "./"
    """
    pass


@router.patch('/change-file-metadata/{file_path:path}')
async def change_file_metadata(
    *, db: AsyncSession = Depends(pg.get_session), update: FileUpdate, old_file_path: str,
) -> FilePublic:
    pass


@router.get('/download-file/{file_path:path}')
async def download_file(
    *,
    db: AsyncSession = Depends(pg.get_session),
    file_path: str,
) -> StreamingResponse:
    """Endpoint for downloading file from file storage"""
    pass


@router.delete('/remove-file/{file_path:path}')
async def remove_file(*, db: AsyncSession = Depends(pg.get_session), file_path: str) -> FilePublic:
    """Endpoint for removing a file from File Storage"""
    pass