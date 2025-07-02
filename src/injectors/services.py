from src.config import config
from src.services import FilesService
import asyncio
from . import connections


async def files_service() -> FilesService:
    session = await connections.pg.acquire_session()
    return FilesService(
        base_dir=config.storage_dir,
        pg=session,
        fc=config.file_config
    )
