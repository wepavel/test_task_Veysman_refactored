from urllib.parse import quote

from fastapi import APIRouter, Depends, File as FastapiFile, UploadFile
from fastapi.responses import StreamingResponse

from src.injectors.services import files_service
from src.services.files import FilePublic, FilesService, FileUpdate

router = APIRouter()


@router.post('/files/{dir_path:path}')
async def create_file(
        *,
        fs: FilesService = Depends(files_service),
        dir_path: str,
        input_file: UploadFile = FastapiFile(...),

) -> FilePublic:
    """Upload a file to storage at the given path."""
    return await fs.add_file(dir_path, input_file)


@router.patch('/files/{file_path:path}')
async def update_file(
        *,
        fs: FilesService = Depends(files_service),
        update: FileUpdate,
        file_path: str,
) -> FilePublic:
    """Update an existing file at the specified path."""
    return await fs.update_file(update, file_path)


@router.get('/files/{file_path:path}/download')
async def download_file(
        *,
        fs: FilesService = Depends(files_service),
        file_path: str,
) -> StreamingResponse:
    """Download a file from storage."""
    file_generator, filename = await fs.get_file(file_path)

    return StreamingResponse(
        file_generator,
        media_type='application/octet-stream',
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{quote(filename, safe='')}"},
    )


@router.get('/files/{file_path:path}')
async def get_file_info(*, fs: FilesService = Depends(files_service), file_path: str) -> FilePublic:
    """Get metadata about a file."""
    return await fs.get_file_info(file_path)


@router.delete('/files/{file_path:path}')
async def delete_file(*, fs: FilesService = Depends(files_service), file_path: str) -> FilePublic:
    """Delete a file from storage."""
    return await fs.delete_file(file_path)


@router.get('/directories/{dir_path:path}')
async def list_directory(*, fs: FilesService = Depends(files_service), dir_path: str) -> list[FilePublic]:
    """List contents of a directory."""
    return await fs.list_dir(dir_path)


@router.get('/files')
async def list_all_files(
        *,
        fs: FilesService = Depends(files_service),
        skip: int = 0,
        limit: int = 10,
) -> list[FilePublic]:
    """Get metadata for all files with pagination."""
    return await fs.list_all_files(skip=skip, limit=limit)
