import asyncio
from contextlib import asynccontextmanager
import logging
import typing as t

from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import async_scoped_session, async_sessionmaker, create_async_engine
from sqlalchemy_utils import create_database, database_exists
from sqlmodel import SQLModel, text
from sqlmodel.ext.asyncio.session import AsyncSession

from ..base_module import (
    ModuleException,
)


class ConnectionsException(ModuleException):
    """."""

    @classmethod
    def acquire_error(cls) -> t.NoReturn:
        raise cls(msg='Сервис временно недоступен', code=503)


class SessionProviderService:
    """."""

    def __init__(
        self,
        # session: async_scoped_session | AsyncSession,
        async_url: URL,
        sync_url: URL,
        user: str,
        logger: logging.Logger,
        schema: str = 'public',
        init_error_timeout: int = 5,
        acquire_attempts: int = 5,
        acquire_error_timeout: int = 1,
        init_statements: list[str] | None = None,
        debug: bool = False,
    ):
        """."""
        self._pg: AsyncSession | async_scoped_session | None = None
        self._init_error_timeout = init_error_timeout
        self._acquire_attempts = acquire_attempts
        self._acquire_error_timeout = acquire_error_timeout
        self._async_url = async_url
        self._sync_url = sync_url
        self._debug = debug
        self._init_statements = init_statements
        self._schema = schema
        self._logger = logger
        self._user = user

    async def _init_db(self):
        engine = create_async_engine(
            url=self._async_url,
            echo=self._debug,
            query_cache_size=0,
        )

        if not database_exists(self._sync_url):
            create_database(self._sync_url)

        async with engine.begin() as conn:
            await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS {self._schema}'))
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

        # session: AsyncSession = self._pg()

        async with self._pg() as session, session.begin():
            self._logger.info(f'Current role is {self._user}')
            await session.exec(text(f'SET ROLE {self._user}'))
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

        return ConnectionsException.acquire_error()

    @asynccontextmanager
    async def get_session(self) -> t.AsyncGenerator[AsyncSession, None]:
        session = await self.acquire_session()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
