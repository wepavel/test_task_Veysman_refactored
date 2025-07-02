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

from src.base_async.base_module import EXC, ErrorCode
from src.config import FileConfig

from ..models import File, FileCreate, FilePublic, FileUpdate


class FilesService:
    """."""

    def __init__(
            self,
            base_dir: str,
            fc: FileConfig,
            pg: AsyncSession,
    ):
        """."""
        self.base_dir = base_dir
        self._logger = getLogger()
        self._fc = fc
        self._pg = pg

    @staticmethod
    def _make_directory(path: str) -> None:
        try:
            os.makedirs(path, exist_ok=True)
        except:
            raise EXC(ErrorCode.FileMoveError)

    @staticmethod
    def _secure_path_join(base_path: str, rel_path: str) -> str:
        base_path = Path(base_path).resolve()
        rel = Path(rel_path.lstrip('/\\'))
        target = (base_path / rel).resolve()
        try:
            target.relative_to(base_path)
        except ValueError:
            raise EXC(ErrorCode.PathUnsafeError)
        return str(target)

    @staticmethod
    async def _select_file_by_id(*, db: AsyncSession, id: str) -> File | None:
        result = await db.exec(select(File).where(File.id == id))
        return result.one_or_none()

    @staticmethod
    async def _select_file_by_path(*, db: AsyncSession, file_path: str) -> File | None:
        p = Path(file_path).resolve()
        stmt = select(File).where(
            File.name == p.stem,
            File.extension == p.suffix,
            File.path == str(p.parent),
        )
        res = await db.exec(stmt)
        return res.one_or_none()

    @staticmethod
    def assembly_full_path(file: File) -> str:
        return f'{file.path}/{file.name}{file.extension}'

    async def add_file(
            self,
            file_path: str,
            file: UploadFile,
    ) -> FilePublic:
        filename = file.filename
        try:
            target_dir = self._secure_path_join(self.base_dir, file_path)
            full_path = self._secure_path_join(target_dir, filename)
        except:
            raise EXC(ErrorCode.PathUnsafeError)

        db_record = await self._select_file_by_path(db=self._pg, file_path=full_path)
        if db_record:
            raise EXC(ErrorCode.FileAlreadyExists)

        self._make_directory(target_dir)

        try:
            async with aiofiles.open(full_path, 'wb') as out_file:
                while chunk := await file.read(self._fc.upload_chunk_size):
                    await out_file.write(chunk)
        except Exception as e:
            self._logger.warning(f'{e}')
            raise EXC(ErrorCode.FileUploadingError)

        db_file = File.from_file_create(FileCreate(file_path=full_path, comment=''))
        self._pg.add(db_file)
        await self._pg.commit()
        await self._pg.refresh(db_file)

        return db_file.to_public_file(self.base_dir)

    async def update_file(
            self,
            update_obj: FileUpdate,
            id: str,
    ) -> FilePublic:
        source_db_record = await self._select_file_by_id(db=self._pg, id=id)
        if not source_db_record:
            raise EXC(ErrorCode.FileNotExists)

        full_old_path = self.assembly_full_path(source_db_record)

        if update_obj.new_dir_path is None:
            target_dir = source_db_record.path
        else:
            try:
                target_dir = self._secure_path_join(self.base_dir, update_obj.new_dir_path)
            except:
                raise EXC(ErrorCode.PathUnsafeError)

        new_base_name = update_obj.name.strip() if update_obj.name else source_db_record.path
        new_file_name = f'{new_base_name}{source_db_record.extension}'
        full_new_path = os.path.join(target_dir, new_file_name)

        changes = {}

        if full_old_path != full_new_path:
            dest_db_record = await self._select_file_by_path(db=self._pg, file_path=full_new_path)
            if dest_db_record:
                raise EXC(ErrorCode.FileAlreadyExists)

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
        self._pg.add(source_db_record)
        await self._pg.commit()
        await self._pg.refresh(source_db_record)

        return source_db_record.to_public_file(self.base_dir)

    @staticmethod
    async def file_generator(file_path: str, chunk_size: int) -> AsyncGenerator[bytes, None]:
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
        db_record = await self._select_file_by_id(db=self._pg, id=id)
        if not db_record:
            raise EXC(ErrorCode.FileNotExists)

        full_path = self.assembly_full_path(db_record)

        return self.file_generator(full_path, chunk_size), f'{db_record.name}{db_record.extension}'

    async def delete_file(self, id: str) -> FilePublic:
        db_record = await self._select_file_by_id(db=self._pg, id=id)
        if not db_record:
            raise EXC(ErrorCode.FileNotExists)
        await self._pg.delete(db_record)
        await self._pg.commit()

        full_path = self.assembly_full_path(db_record)
        await asyncio.to_thread(os.remove, full_path)

        return db_record.to_public_file(self.base_dir)

    async def get_file_info(self, id: str) -> FilePublic:
        db_record = await self._select_file_by_id(db=self._pg, id=id)
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
            try:
                dir_path = self._secure_path_join(self.base_dir, prefix)
            except:
                raise EXC(ErrorCode.PathUnsafeError)

            stmt = select(File).order_by(File.id).where(File.path == dir_path).offset(skip).limit(limit)

        result = await self._pg.exec(stmt)
        return [file.to_public_file(self.base_dir) for file in result]
