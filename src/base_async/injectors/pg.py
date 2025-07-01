import asyncio
from logging import getLogger

from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import async_scoped_session, async_sessionmaker, create_async_engine
from sqlalchemy_utils import create_database, database_exists
from sqlmodel import SQLModel, text
from sqlmodel.ext.asyncio.session import AsyncSession

from ..base_module import EXC, ErrorCode, PgConfig


class AsyncPgConnectionInj:
    """."""

    def __init__(
            self,
            conf: PgConfig,
            init_error_timeout: int = 5,
            acquire_attempts: int = 5,
            acquire_error_timeout: int = 5,
            init_statements: list[str] | None = None,
    ):
        """."""
        self._conf = conf
        self._init_error_timeout = init_error_timeout
        self._acquire_attempts = acquire_attempts
        self._acquire_error_timeout = acquire_error_timeout
        self._init_statements = init_statements or []
        self._pg: async_scoped_session | AsyncSession | None = None
        self._logger = getLogger(__name__)

    def build_url(self, driver: str):
        return URL.create(
            f"postgresql{'+asyncpg' if driver == 'async' else ''}",
            username=self._conf.user,
            password=self._conf.password,
            host=self._conf.host,
            port=self._conf.port,
            database=self._conf.database,
        )

    async def _init_db(self):
        engine = create_async_engine(
            url=self.build_url('async'),
            echo=self._conf.debug,
            query_cache_size=0,
        )

        if not database_exists(self.build_url('sync')):
            create_database(self.build_url('sync'))

        async with engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {self._conf.schema}'))
            for stmt in self._init_statements:
                await conn.execute(text(stmt))
            await conn.run_sync(SQLModel.metadata.create_all)

        async_session_fabric = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        self._pg = async_scoped_session(
            async_session_fabric,
            scopefunc=asyncio.current_task,
        )

    async def init_db(self):
        while True:
            try:
                self._logger.debug('Инициализация базы данных')
                return await self._init_db()
            except Exception as e:
                self._logger.error('Ошибка инициализации базы данны, ожидание', exc_info=True, extra={'e': e})
                await asyncio.sleep(self._init_error_timeout)

    async def _acquire_session(self) -> AsyncSession:
        if not self._pg:
            await self._init_db()

        async with self._pg() as session, session.begin():
            self._logger.info(f'Current role is {self._conf.user}')
            await session.exec(text(f'SET ROLE {self._conf.user}'))
            return session

    async def acquire_session(self) -> AsyncSession:
        for i in range(self._acquire_attempts):
            try:
                return await self._acquire_session()
            except Exception as e:
                self._logger.warning(
                    'Ошибка инициализации сессии, ожидание повтора',
                    exc_info=True,
                    extra={'e': e, 'cur': i, 'max': self._acquire_attempts},
                )
                await asyncio.sleep(self._acquire_error_timeout)

        raise EXC(ErrorCode.ConnectionsError)

    async def setup(self):
        await self.init_db()

    def get_session(self) -> async_scoped_session[AsyncSession]:
        return self._pg
