from fastapi import APIRouter, Depends

from src.injectors.services import files_service
from src.models import FilePublic
from src.services.files import FilesService

router = APIRouter()


@router.get('/get-file-info/{file_path:path}')
async def get_file_info(*, fs: FilesService = Depends(files_service), file_path: str) -> FilePublic:
    """Endpoint for getting file info."""
    return await fs.get_file_info(file_path)


@router.get('/list-dir/{dir_path:path}')
async def list_dir(*, fs: FilesService = Depends(files_service), dir_path: str) -> list[FilePublic]:
    """Endpoint for listing desired directory.
    If you want to list files from root dir - use ".", "/" or "./"
    """
    return await fs.list_dir(dir_path)


@router.get('/get-all-files-info')
async def get_all_files_info(
    *,
    fs: FilesService = Depends(files_service),
    skip: int = 0,
    limit: int = 10,
) -> list[FilePublic]:
    """Endpoint for getting all files data in database"""
    return await fs.list_all_files(skip=skip, limit=limit)
