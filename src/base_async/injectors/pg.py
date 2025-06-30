from sqlalchemy.engine.url import URL

from src.base_async.base_module.logger import get_logger

from ..base_module import (
    PgConfig,
    ThreadIsolatedSingleton,
)
from ..services.session_provider import SessionProviderService


class AsyncPgConnectionInj(metaclass=ThreadIsolatedSingleton):
    """."""

    def __init__(
        self,
        conf: PgConfig,
        init_statements: list[str] | None = None,
    ):
        """."""
        self._conf = conf
        self._init_statements = init_statements or []
        # self._pg: async_scoped_session | AsyncSession | None = None
        self._logger = get_logger()

    def build_url(self, driver: str):
        return URL.create(
            f"postgresql{'+asyncpg' if driver == 'async' else ''}",
            username=self._conf.user,
            password=self._conf.password,
            host=self._conf.host,
            port=self._conf.port,
            database=self._conf.database,
        )

    async def setup(self):
        session_provider = SessionProviderService(
            self.build_url('async'),
            self.build_url('sync'),
            self._conf.user,
            self._logger,
            schema=self._conf.schema,
            init_statements=self._init_statements,
        )
        await session_provider.init_db()

    def get_session_provider(self) -> SessionProviderService:
        return SessionProviderService(
            self.build_url('async'),
            self.build_url('sync'),
            self._conf.user,
            self._logger,
            schema=self._conf.schema,
            init_statements=self._init_statements,
        )
