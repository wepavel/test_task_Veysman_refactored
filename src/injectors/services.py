from src.config import config
from src.services import FilesService

from . import connections


def files_service() -> FilesService:
    return FilesService(base_dir=config.storage_dir, pg=connections.pg.get_session(), fc=config.file_config)
