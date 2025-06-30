from src.base_async.services import TimezoneService
from src.config import config
from src.services import CRUDFileService, FilesService

from . import connections


def files_service() -> FilesService:
    return FilesService(
        pg=CRUDFileService(),
        base_dir=config.storage_dir,
        tz=TimezoneService(config.timezone),
        session_provider=connections.pg.get_session_provider(),
    )
