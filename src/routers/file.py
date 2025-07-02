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
        input_file: UploadFile = FastapiFile(
            ...,
        ),
) -> FilePublic:
    """Upload a file to storage at the given path."""
    return await fs.add_file(dir_path, input_file)


@router.patch('/files/{id}')
async def update_file(
        *,
        fs: FilesService = Depends(files_service),
        update: FileUpdate,
        id: str,
) -> FilePublic:
    """Update an existing file at the specified path."""
    return await fs.update_file(update, id)


@router.get('/files/{id}/download')
async def download_file(
        *,
        fs: FilesService = Depends(files_service),
        id: str,
) -> StreamingResponse:
    """Download a file from storage."""
    file_generator, filename = await fs.get_file(id)

    return StreamingResponse(
        file_generator,
        media_type='application/octet-stream',
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{quote(filename, safe='')}"},
    )


@router.get('/files/{id}')
async def get_file_info(*, fs: FilesService = Depends(files_service), id: str) -> FilePublic:
    """Get metadata about a file."""
    return await fs.get_file_info(id)


@router.delete('/files/{id}')
async def delete_file(*, fs: FilesService = Depends(files_service), id: str) -> FilePublic:
    """Delete a file from storage."""
    return await fs.delete_file(id)


# @router.get('/files/prefix/{path:path}')
# async def list_directory(*, fs: FilesService = Depends(files_service), prefix: str) -> list[FilePublic]:
#     """List contents of a directory."""
#     return await fs.list_dir(prefix)


@router.get('/files/')
async def list_all_files(
        *,
        fs: FilesService = Depends(files_service),
        prefix: str | None = None,
        skip: int = 0,
        limit: int = 10,
) -> list[FilePublic]:
    """Get metadata for files with pagination."""
    if prefix is None:
        return await fs.list_all_files(skip=skip, limit=limit)
    else:
        return await fs.list_dir(prefix)
