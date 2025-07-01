import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from logging import getLogger
import os
from pathlib import Path
import shutil

import aiofiles
from fastapi import UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from src.base_async.base_module import EXC, ErrorCode
from src.base_async.injectors import AsyncPgConnectionInj
from src.base_async.services import TimezoneService

from ..base_async.services import AsyncSessionContextService
from ..models import File, FileCreate, FilePublic, FileUpdate
from  src.config import FileConfig
from .pg import CRUDFileService


class FilesService:
    """."""

    def __init__(
            self,
            base_dir: str,
            fc: FileConfig,
            tz: TimezoneService,
            pg: CRUDFileService,
            db_inj: AsyncPgConnectionInj
    ):
        """."""
        self.base_dir = base_dir
        self._logger = getLogger()
        self._tz = tz
        self._pg = pg
        self._session_ctx = AsyncSessionContextService(db_inj)
        self._fc = fc

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
            file_path: str,
            session: AsyncSession,
            db: CRUDFileService,
            should_exist: bool = True,
    ) -> bool:
        file_on_disk = os.path.isfile(file_path)
        db_record = await db.get_by_path(db=session, file_path=file_path)

        return (file_on_disk and db_record) if should_exist else (not file_on_disk and not db_record)

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

        async with self._session_ctx as session:
            if not await self._check_file(full_path, session, self._pg, should_exist=False):
                raise EXC(ErrorCode.FileAlreadyExists)

            self._make_directory(target_dir)

            try:
                async with aiofiles.open(full_path, 'wb') as out_file:
                    while chunk := await file.read(self._fc.upload_chunk_size):
                        await out_file.write(chunk)
            except:
                raise EXC(ErrorCode.FileUploadingError)

            db_file = File.from_file_create(FileCreate(file_path=full_path, comment=''))
            saved_file = await self._pg.create(db=session, obj_in=db_file)

            return saved_file.to_public_file(self.base_dir, self._tz.get_current_timezone())

    async def update_file(
            self,
            update_obj: FileUpdate,
            old_file_path: str,
    ) -> FilePublic:
        try:
            full_old_path = self._secure_path_join(self.base_dir, old_file_path)
        except:
            raise EXC(ErrorCode.PathUnsafeError)
        old_base_name, old_ext, old_dir = self._get_file_parts(full_old_path)

        if update_obj.new_dir_path is None:
            target_dir = old_dir
        else:
            try:
                target_dir = self._secure_path_join(self.base_dir, update_obj.new_dir_path)
            except:
                raise EXC(ErrorCode.PathUnsafeError)

        new_base_name = update_obj.name.strip() if update_obj.name else old_base_name
        new_file_name = f'{new_base_name}{old_ext}'
        full_new_path = os.path.join(target_dir, new_file_name)

        needs_move = full_old_path != full_new_path

        async with self._session_ctx as session:
            if not await self._check_file(full_old_path, session, self._pg, True):
                raise EXC(ErrorCode.FileNotExists)

            if not (db_obj := await self._pg.get_by_path(db=session, file_path=full_old_path)):
                raise EXC(ErrorCode.FileNotExists)
            changes = {}

            if needs_move:
                if not await self._check_file(full_new_path, session, self._pg, False):
                    raise EXC(ErrorCode.FileAlreadyExists)
                self._make_directory(target_dir)
                try:
                    await self._move_file_async(full_old_path, full_new_path)
                    new_base_name, _, new_dir = self._get_file_parts(full_new_path)
                    changes['path'] = new_dir
                    changes['name'] = new_base_name
                except:
                    raise EXC(ErrorCode.FileMoveError)

            if update_obj.comment is not None and update_obj.comment != db_obj.comment:
                changes['comment'] = update_obj.comment

            changes['updated_at'] = datetime.now(timezone.utc)

            updated_obj = await self._pg.update(db=session, db_obj=db_obj, obj_in=changes)
            return updated_obj.to_public_file(self.base_dir, self._tz.get_current_timezone())

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
            file_path: str,
            chunk_size: int = 1024,
    ) -> tuple[AsyncGenerator[bytes, None], str]:
        try:
            full_path = self._secure_path_join(self.base_dir, file_path)
        except:
            raise EXC(ErrorCode.PathUnsafeError)

        async with self._session_ctx as session:
            if not await self._check_file(full_path, session, self._pg, True):
                raise EXC(ErrorCode.FileNotExists)

        base_name, ext, _ = self._get_file_parts(file_path)
        return self.file_generator(full_path, chunk_size), f'{base_name}{ext}'

    async def delete_file(self, file_path: str) -> FilePublic:
        try:
            full_path = self._secure_path_join(self.base_dir, file_path)
        except:
            raise EXC(ErrorCode.PathUnsafeError)

        async with self._session_ctx as session:
            if not await self._check_file(full_path, session, self._pg, True):
                raise EXC(ErrorCode.FileNotExists)

            deleted_obj = await self._pg.remove_by_path(db=session, file_path=full_path)

        await asyncio.to_thread(os.remove, full_path)

        return deleted_obj.to_public_file(self.base_dir, self._tz.get_current_timezone())

    async def get_file_info(self, file_path: str) -> FilePublic:
        try:
            file_path = self._secure_path_join(self.base_dir, file_path)
        except:
            raise EXC(ErrorCode.PathUnsafeError)
        async with self._session_ctx as session:
            if not (file := await self._pg.get_by_path(db=session, file_path=file_path)):
                raise EXC(ErrorCode.FileNotExists)
        return file.to_public_file(self.base_dir, self._tz.get_current_timezone())

    async def list_dir(self, dir_path: str) -> list[FilePublic]:
        try:
            dir_path = self._secure_path_join(self.base_dir, dir_path)
        except:
            raise EXC(ErrorCode.PathUnsafeError)
        async with self._session_ctx as session:
            files = await self._pg.list_dir(db=session, dir_path=dir_path)

        return [file.to_public_file(self.base_dir, self._tz.get_current_timezone()) for file in files]

    async def list_all_files(
            self,
            skip: int = 0,
            limit: int = 10,
    ) -> list[FilePublic]:
        async with self._session_ctx as session:
            files = await self._pg.get_multi(db=session, skip=skip, limit=limit)
        return [file.to_public_file(self.base_dir, self._tz.get_current_timezone()) for file in files]
