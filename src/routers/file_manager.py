from urllib.parse import quote

from fastapi import APIRouter, Depends, File as FastapiFile, UploadFile
from fastapi.responses import StreamingResponse

from src.injectors.services import files_service
from src.services.files import FilePublic, FilesService, FileUpdate

CHUNK_SIZE = 1024 * 1024 * 5  # 5 MB
FILE_MAX_SIZE = 100 * 1024 * 1024  # 100 MB

CHECK_FILE_DELAY = 0.5
MAX_RETRIES = 10


router = APIRouter()


@router.post('/upload-file/{file_path:path}')
async def upload_file(
    *,
    fs: FilesService = Depends(files_service),
    file_path: str,
    input_file: UploadFile = FastapiFile(..., max_size=FILE_MAX_SIZE),
) -> FilePublic:
    """Endpoint for adding file to datastorage.
    If you want to save fie in root dir - use ".", "/" or "./"
    """
    return await fs.add_file(file_path, input_file, CHUNK_SIZE)


@router.patch('/update-file/{old_file_path:path}')
async def update_file(
    *,
    fs: FilesService = Depends(files_service),
    update: FileUpdate,
    old_file_path: str,
) -> FilePublic:
    return await fs.update_file(update, old_file_path)


@router.get('/download-file/{file_dest_dir:path}')
async def download_file(
    *,
    fs: FilesService = Depends(files_service),
    file_dest_dir: str,
) -> StreamingResponse:
    file_generator, filename = await fs.get_file(file_dest_dir)

    return StreamingResponse(
        file_generator,
        media_type='application/octet-stream',
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{quote(filename, safe='')}"},
    )


@router.delete('/remove-file/{file_path:path}')
async def remove_file(*, fs: FilesService = Depends(files_service), file_path: str) -> FilePublic:
    """Endpoint for removing a file from File Storage"""
    return await fs.delete_file(file_path)
