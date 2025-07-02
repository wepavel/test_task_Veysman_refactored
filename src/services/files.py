import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime
from logging import getLogger
import os
from pathlib import Path
import shutil

import aiofiles
from fastapi import UploadFile
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import async_scoped_session

from src.base_async.base_module import EXC, ErrorCode
from src.config import FileConfig

from ..models import File, FileCreate, FilePublic, FileUpdate


class FilesService:
    """."""

    def __init__(
            self,
            base_dir: str,
            fc: FileConfig,
            pg: async_scoped_session[AsyncSession],
    ):
        """."""
        self.base_dir = base_dir
        self._logger = getLogger()
        self._fc = fc
        self._pg = pg

    @classmethod
    def _make_directory(cls, path: str) -> None:
        try:
            os.makedirs(path, exist_ok=True)
        except:
            raise EXC(ErrorCode.FileMoveError)

    @classmethod
    def _is_file(cls, path: str, invert: bool=False) -> None:
        if not invert:
            if not os.path.isfile(path):
                raise EXC(ErrorCode.FileNotExists)
        else:
            if os.path.isfile(path):
                raise EXC(ErrorCode.FileAlreadyExists)

    @classmethod
    def _secure_path_join(cls, base_path: str, rel_path: str) -> str:
        base_path = Path(base_path).resolve()
        rel = Path(rel_path.lstrip('/\\'))
        target = (base_path / rel).resolve()
        try:
            target.relative_to(base_path)
        except ValueError:
            raise EXC(ErrorCode.PathUnsafeError)
        return str(target)

    @classmethod
    async def _select_file_by_id(cls, *, db: AsyncSession, id: str) -> File | None:
        result = await db.exec(select(File).where(File.id == id))
        return result.one_or_none()

    @classmethod
    async def _select_file_by_path(cls, *, db: AsyncSession, file_path: str) -> File | None:
        p = Path(file_path).resolve()
        stmt = select(File).where(
            File.name == p.stem,
            File.extension == p.suffix,
            File.path == str(p.parent),
        )
        res = await db.exec(stmt)
        return res.one_or_none()


    async def add_file(
            self,
            file_path: str,
            file: UploadFile,
    ) -> FilePublic:
        filename = file.filename
        target_dir = self._secure_path_join(self.base_dir, file_path)
        full_path = self._secure_path_join(target_dir, filename)
        async with self._pg() as session, session.begin():
            db_record = await self._select_file_by_path(db=session, file_path=full_path)
        if db_record:
            raise EXC(ErrorCode.FileAlreadyExists)
        self._is_file(full_path, invert=True)

        self._make_directory(target_dir)

        try:
            async with aiofiles.open(full_path, 'wb') as out_file:
                while chunk := await file.read(self._fc.upload_chunk_size):
                    await out_file.write(chunk)
        except Exception as e:
            self._logger.warning(f'{e}')
            raise EXC(ErrorCode.FileUploadingError)

        async with self._pg() as session, session.begin():
            db_file = File.from_file_create(FileCreate(file_path=full_path, comment=''))
            self._pg.add(db_file)
            await self._pg.flush()
            await self._pg.refresh(db_file)

        return db_file.to_public_file(self.base_dir)

    async def update_file(
            self,
            update_obj: FileUpdate,
            id: str,
    ) -> FilePublic:
        async with self._pg() as session, session.begin():
            source_db_record = await self._select_file_by_id(db=session, id=id)
        if not source_db_record:
            raise EXC(ErrorCode.FileNotExists)

        full_old_path = source_db_record.get_full_path()
        self._is_file(full_old_path)

        if update_obj.new_dir_path is None:
            target_dir = source_db_record.path
        else:
            target_dir = self._secure_path_join(self.base_dir, update_obj.new_dir_path)

        new_base_name = update_obj.name.strip() if update_obj.name else source_db_record.path
        new_file_name = f'{new_base_name}{source_db_record.extension}'
        full_new_path = os.path.join(target_dir, new_file_name)

        changes = {}
        if full_old_path != full_new_path:
            async with self._pg() as session, session.begin():
                dest_db_record = await self._select_file_by_path(db=session, file_path=full_new_path)
            if dest_db_record:
                raise EXC(ErrorCode.FileAlreadyExists)

            self._is_file(full_new_path, invert=True)

            self._make_directory(target_dir)
            try:
                await asyncio.to_thread(shutil.move, full_old_path, full_new_path)
                p = Path(full_new_path)
                changes['path'] = str(p.parent)
                changes['name'] = p.stem
            except:
                raise EXC(ErrorCode.FileMoveError)

        if update_obj.comment is not None and update_obj.comment != source_db_record.comment:
            changes['comment'] = update_obj.comment

        changes['updated_at'] = datetime.now()

        source_db_record.update(changes)
        async with self._pg() as session, session.begin():
            session.add(source_db_record)
            await session.flush()
            await session.refresh(source_db_record)

        return source_db_record.to_public_file(self.base_dir)

    @classmethod
    async def file_generator(cls, file_path: str, chunk_size: int) -> AsyncGenerator[bytes, None]:
        try:
            async with aiofiles.open(file_path, mode='rb') as f:
                while True:
                    chunk = await f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        except:
            raise EXC(ErrorCode.FileDownloadingError)

    async def get_file(
            self,
            id: str,
            chunk_size: int = 1024,
    ) -> tuple[AsyncGenerator[bytes, None], str]:
        async with self._pg() as session, session.begin():
            db_record = await self._select_file_by_id(db=session, id=id)

        if not db_record:
            raise EXC(ErrorCode.FileNotExists)

        full_path = db_record.get_full_path()
        self._is_file(full_path)

        return self.file_generator(full_path, chunk_size), f'{db_record.name}{db_record.extension}'

    async def delete_file(self, id: str) -> FilePublic:
        async with self._pg() as session, session.begin():
            db_record = await self._select_file_by_id(db=session, id=id)
        if not db_record:
            raise EXC(ErrorCode.FileNotExists)

        full_path = db_record.get_full_path()
        self._is_file(full_path)

        async with self._pg() as session, session.begin():
            await session.delete(db_record)
            await session.flush()

        await asyncio.to_thread(os.remove, full_path)

        return db_record.to_public_file(self.base_dir)

    async def get_file_info(self, id: str) -> FilePublic:
        async with self._pg() as session, session.begin():
            db_record = await self._select_file_by_id(db=session, id=id)
        if not db_record:
            raise EXC(ErrorCode.FileNotExists)

        return db_record.to_public_file(self.base_dir)

    async def list_files(
            self,
            prefix: str = None,
            skip: int = 0,
            limit: int = 10,
    ) -> list[FilePublic]:
        if prefix is None:
            stmt = select(File).order_by(File.id).offset(skip).limit(limit)
        else:
            dir_path = self._secure_path_join(self.base_dir, prefix)
            stmt = select(File).order_by(File.id).where(File.path == dir_path).offset(skip).limit(limit)

        async with self._pg() as session, session.begin():
            result = await session.exec(stmt)
        return [file.to_public_file(self.base_dir) for file in result]
