from sqlmodel.ext.asyncio.session import AsyncSession

from src.base_async.injectors import AsyncPgConnectionInj


class AsyncSessionContextService:
    def __init__(self, db_inj: AsyncPgConnectionInj):
        self.db_inj = db_inj
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> AsyncSession:
        self.session = await self.db_inj.acquire_session()
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session is None:
            return

        try:
            if exc_type:
                await self.session.rollback()
            else:
                await self.session.commit()
        finally:
            await self.session.close()
