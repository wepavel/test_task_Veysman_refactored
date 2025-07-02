from src.config import config
from src.services import FilesService
from . import connections


async def files_service() -> FilesService:
    session = await connections.pg.acquire_session()
    return FilesService(
        base_dir=config.storage_dir,
        pg=session,
        upload_chunk_size=config.file_config.upload_chunk_size
    )
