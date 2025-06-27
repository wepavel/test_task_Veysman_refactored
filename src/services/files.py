
from sqlmodel.ext.asyncio.session import AsyncSession as PGSession

from src.base_async.base_module import (
    # sa_operator,
    ModuleException,
    # ClassesLoggerAdapter
    get_logger
)
import os

def secure_path_join(base_path: str, file_path: str) -> str:
    if file_path in ('', '/'):
        return os.path.abspath(base_path)
    combined_path = os.path.join(base_path, file_path)
    normalized_path = os.path.abspath(os.path.normpath(combined_path))
    # Verify that the final path starts with BASE_DIR
    if not normalized_path.startswith(base_path):
        raise ValueError('Attempt to escape the allowed directory')
    return normalized_path

class FilesService:
    """."""
    def __init__(
            self,
            pg_connection: PGSession
    ):
        """."""
        self._pg = pg_connection
        self._logger = get_logger()
