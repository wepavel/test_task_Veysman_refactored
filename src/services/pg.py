from pathlib import Path

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.base_async.services import CRUDBaseService
from src.models import File


class CRUDFileService(CRUDBaseService[File, File, File]):
    """."""

    async def get_by_path(self, db: AsyncSession, file_path: str) -> File | None:
        p = Path(file_path).resolve()
        name = p.stem
        extension = p.suffix
        directory = str(p.parent)

        # Выполняем запрос: находим файл с заданными name, extension и directory (path)
        statement = select(self.model).where(
            self.model.name == name,
            self.model.extension == extension,
            self.model.path == directory,
        )
        result = await db.exec(statement)
        return result.one_or_none()

    async def remove_by_path(self, db: AsyncSession, file_path: str) -> File | None:
        file_obj = await self.get_by_path(db, file_path)
        if file_obj:
            await db.delete(file_obj)
            await db.flush()
        return file_obj

    async def list_dir(self, db: AsyncSession, dir_path: str) -> list[File]:
        statement = select(self.model).where(self.model.path == dir_path)
        results = await db.exec(statement)
        files = results.all()
        return files
