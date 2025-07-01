from src.base_async.services import TimezoneService
from src.config import config
from src.services import CRUDFileService, FilesService

from . import connections


def files_service() -> FilesService:
    return FilesService(
        pg=CRUDFileService(),
        base_dir=config.storage_dir,
        tz=TimezoneService(config.timezone),
        db_inj=connections.pg,
        fc=config.file_config
    )
