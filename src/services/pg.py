from logging import getLogger
from pathlib import Path
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.models import File


class CRUDFileService:
    """."""

    def __init__(self) -> None:
        self._logger = getLogger(__name__)

    @staticmethod
    def merge_dicts(d1: dict, d2: dict) -> dict:
        for k, v in d2.items():
            if isinstance(v, dict) and isinstance(d1.get(k), dict):
                CRUDFileService.merge_dicts(d1.setdefault(k, {}), v)
            else:
                d1[k] = v
        return d1

    @staticmethod
    async def get(*, db: AsyncSession, id: str) -> File | None:
        result = await db.exec(select(File).where(File.id == id))
        return result.one_or_none()

    @staticmethod
    async def get_multi(*, db: AsyncSession, skip: int = 0, limit: int = 100) -> list[File]:
        stmt = select(File).order_by(File.id).offset(skip).limit(limit)
        result = await db.exec(stmt)
        return list(result.all())

    @staticmethod
    async def create(*, db: AsyncSession, obj_in: File) -> File:
        db.add(obj_in)
        await db.flush()
        await db.refresh(obj_in)
        return obj_in

    @staticmethod
    async def update(*, db: AsyncSession, db_obj: File, obj_in: dict[str, Any] | File) -> File:
        stored_data = db_obj.model_dump(exclude_none=True)

        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        merged = CRUDFileService.merge_dicts(stored_data, update_data)

        for field, value in merged.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def get_by_path(*, db: AsyncSession, file_path: str) -> File | None:
        p = Path(file_path).resolve()
        stmt = select(File).where(
            File.name == p.stem,
            File.extension == p.suffix,
            File.path == str(p.parent),
        )
        res = await db.exec(stmt)
        return res.one_or_none()

    @staticmethod
    async def remove_by_path(*, db: AsyncSession, file_path: str) -> File | None:
        file_obj = await CRUDFileService.get_by_path(db=db, file_path=file_path)
        if file_obj:
            await db.delete(file_obj)
            await db.flush()
        return file_obj

    @staticmethod
    async def list_dir(*, db: AsyncSession, dir_path: str) -> list[File]:
        stmt = select(File).where(File.path == dir_path)
        res = await db.exec(stmt)
        return res.all()
