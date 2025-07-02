import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from logging import getLogger
import os
from pathlib import Path
import shutil
from typing import Any

import aiofiles
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import async_scoped_session
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
            pg: async_scoped_session[AsyncSession],
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
            raise EXC(ErrorCode.FileUploadingError)

    @staticmethod
    async def _move_file_async(old_path: str, new_path: str) -> str:
        await asyncio.to_thread(shutil.move, old_path, new_path)
        return new_path

    @staticmethod
    async def _check_file(
            file_identifier: str, session: AsyncSession, should_exist: bool = True, get_file_type: str = 'path'
    ) -> tuple[bool, File]:

        if get_file_type == 'path':
            db_record = await FilesService._get_file_by_path(db=session, file_path=file_identifier)
        else:
            db_record = await FilesService._get_file_by_id(db=session, id=file_identifier)

        file_in_disc = False
        if db_record:
            file_in_disc = os.path.isfile(f'{db_record.path}/{db_record.name}{db_record.extension}')

        file_exists = (db_record and file_in_disc) if should_exist else (not file_in_disc and not db_record)

        return file_exists, db_record

    @staticmethod
    def _get_file_parts(path: str) -> tuple[str, str, str]:
        p = Path(path)
        return p.stem, p.suffix, str(p.parent)

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
    async def _get_file_by_id(*, db: AsyncSession, id: str) -> File | None:
        result = await db.exec(select(File).where(File.id == id))
        return result.one_or_none()

    @staticmethod
    async def _get_multi(*, db: AsyncSession, skip: int = 0, limit: int = 100) -> list[File]:
        stmt = select(File).order_by(File.id).offset(skip).limit(limit)
        result = await db.exec(stmt)
        return list(result.all())

    @staticmethod
    async def _get_file_by_path(*, db: AsyncSession, file_path: str) -> File | None:
        p = Path(file_path).resolve()
        stmt = select(File).where(
            File.name == p.stem,
            File.extension == p.suffix,
            File.path == str(p.parent),
        )
        res = await db.exec(stmt)
        return res.one_or_none()


    @staticmethod
    async def _update(*, db: AsyncSession, db_obj: File, obj_in: dict[str, Any]) -> File:
        db_obj.update(obj_in)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def _remove_by_id(*, db: AsyncSession, id: str) -> File:
        obj = await FilesService._get_file_by_id(db=db, id=id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj

    @staticmethod
    async def _list_dir(*, db: AsyncSession, dir_path: str) -> list[File]:
        stmt = select(File).where(File.path == dir_path)
        res = await db.exec(stmt)
        return res.all()

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

        async with self._pg() as session:
            file_exists, _ = await self._check_file(file_path, session, should_exist=False, get_file_type='path')
            if not file_exists:
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
            session.add(db_file)
            await session.commit()
            await session.refresh(db_file)

            return db_file.to_public_file(self.base_dir)

    async def update_file(
            self,
            update_obj: FileUpdate,
            id: str,
    ) -> FilePublic:
        async with self._pg() as session:
            file_exists, file_record = await self._check_file(id, session, should_exist=True, get_file_type='id')
        if not file_exists:
            raise EXC(ErrorCode.FileNotExists)

        full_old_path = self.assembly_full_path(file_record)

        if update_obj.new_dir_path is None:
            target_dir = file_record.path
        else:
            try:
                target_dir = self._secure_path_join(self.base_dir, update_obj.new_dir_path)
            except:
                raise EXC(ErrorCode.PathUnsafeError)

        new_base_name = update_obj.name.strip() if update_obj.name else file_record.path
        new_file_name = f'{new_base_name}{file_record.extension}'
        full_new_path = os.path.join(target_dir, new_file_name)

        needs_move = full_old_path != full_new_path

        async with self._pg() as session:
            changes = {}

            if needs_move:
                file_not_exists, _ = await self._check_file(
                    full_new_path, session, should_exist=False, get_file_type='path'
                )
                if not file_not_exists:
                    raise EXC(ErrorCode.FileAlreadyExists)
                self._make_directory(target_dir)
                try:
                    await self._move_file_async(full_old_path, full_new_path)
                    new_base_name, _, new_dir = self._get_file_parts(full_new_path)
                    changes['path'] = new_dir
                    changes['name'] = new_base_name
                except:
                    raise EXC(ErrorCode.FileMoveError)

            if update_obj.comment is not None and update_obj.comment != file_record.comment:
                changes['comment'] = update_obj.comment

            changes['updated_at'] = datetime.now(timezone.utc)

            updated_obj = await self._update(db=session, db_obj=file_record, obj_in=changes)
            return updated_obj.to_public_file(self.base_dir)

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
        async with self._pg() as session:
            file_exists, file_record = await self._check_file(id, session, should_exist=True, get_file_type='id')
        if not file_exists:
            raise EXC(ErrorCode.FileNotExists)

        full_path = self.assembly_full_path(file_record)

        return self.file_generator(full_path, chunk_size), f'{file_record.name}{file_record.extension}'

    async def delete_file(self, id: str) -> FilePublic:
        async with self._pg() as session:
            file = await FilesService._get_file_by_id(db=session, id=id)
            if not file:
                raise EXC(ErrorCode.FileNotExists)
            await session.delete(file)
            await session.commit()

        full_path = f'{file.path}/{file.name}{file.extension}'
        await asyncio.to_thread(os.remove, full_path)

        return file.to_public_file(self.base_dir)

    async def get_file_info(self, id: str) -> FilePublic:
        async with self._pg() as session:
            file_exists, file_record = await self._check_file(id, session, should_exist=True, get_file_type='id')
        if not file_exists:
            raise EXC(ErrorCode.FileNotExists)

        return file_record.to_public_file(self.base_dir)

    async def list_dir(self, dir_path: str) -> list[FilePublic]:
        try:
            dir_path = self._secure_path_join(self.base_dir, dir_path)
        except:
            raise EXC(ErrorCode.PathUnsafeError)
        async with self._pg() as session:
            files = await self._list_dir(db=session, dir_path=dir_path)

        return [file.to_public_file(self.base_dir) for file in files]

    async def list_all_files(
            self,
            skip: int = 0,
            limit: int = 10,
    ) -> list[FilePublic]:
        async with self._pg() as session:
            files = await self._get_multi(db=session, skip=skip, limit=limit)
        return [file.to_public_file(self.base_dir) for file in files]
