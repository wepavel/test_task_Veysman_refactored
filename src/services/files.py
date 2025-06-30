import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import os
from pathlib import Path
import shutil

import aiofiles
from fastapi import UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from src.base_async.base_module import EXC, ErrorCode, get_logger
from src.base_async.services import TimezoneService

from ..base_async.services import SessionProviderService
from ..models import File, FileCreate, FilePublic, FileUpdate
from .pg import CRUDFileService


def secure_path_join(base_path: str, rel_path: str) -> str:
    base_path = Path(base_path).resolve()
    rel = Path(rel_path.lstrip('/\\'))
    target = (base_path / rel).resolve()
    try:
        target.relative_to(base_path)
    except ValueError:
        raise EXC(ErrorCode.PathUnsafeError)
    return str(target)


def get_file_parts(path: str) -> tuple[str, str, str]:
    p = Path(path)
    return p.stem, p.suffix, str(p.parent)


async def check_file(
    file_path: str,
    session: AsyncSession,
    db: CRUDFileService,
    should_exist: bool = True,
) -> bool:
    file_on_disk = os.path.isfile(file_path)
    db_record = await db.get_by_path(db=session, file_path=file_path)

    return (file_on_disk and db_record) if should_exist else (not file_on_disk and not db_record)


async def move_file_async(old_path: str, new_path: str) -> str:
    await asyncio.to_thread(shutil.move, old_path, new_path)
    return new_path


def make_directory(path: str) -> None:
    try:
        os.makedirs(path, exist_ok=True)
    except:
        raise EXC(ErrorCode.FileUploadingError)


class FilesService:
    """."""

    def __init__(
        self, base_dir: str, tz: TimezoneService, pg: CRUDFileService, session_provider: SessionProviderService
    ):
        """."""
        self.base_dir = base_dir
        self._logger = get_logger()
        self._tz = tz
        self._pg = pg
        self._session_provider = session_provider

    async def add_file(
        self,
        file_path: str,
        file: UploadFile,
        chunk_size: int = 1024,
    ) -> FilePublic:
        filename = file.filename
        try:
            target_dir = secure_path_join(self.base_dir, file_path)
            full_path = secure_path_join(target_dir, filename)
        except:
            raise EXC(ErrorCode.PathUnsafeError)

        async with self._session_provider.get_session() as session:
            if not await check_file(full_path, session, self._pg, should_exist=False):
                raise EXC(ErrorCode.FileAlreadyExists)

            make_directory(target_dir)

            try:
                async with aiofiles.open(full_path, 'wb') as out_file:
                    while chunk := await file.read(chunk_size):
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
            full_old_path = secure_path_join(self.base_dir, old_file_path)
        except:
            raise EXC(ErrorCode.PathUnsafeError)
        old_base_name, old_ext, old_dir = get_file_parts(full_old_path)

        if update_obj.new_dir_path is None:
            target_dir = old_dir
        else:
            try:
                target_dir = secure_path_join(self.base_dir, update_obj.new_dir_path)
            except:
                raise EXC(ErrorCode.PathUnsafeError)

        new_base_name = update_obj.name.strip() if update_obj.name else old_base_name
        new_file_name = f'{new_base_name}{old_ext}'
        full_new_path = os.path.join(target_dir, new_file_name)

        needs_move = full_old_path != full_new_path

        async with self._session_provider.get_session() as session:
            if not await check_file(full_old_path, session, self._pg, True):
                raise EXC(ErrorCode.FileNotExists)

            if not (db_obj := await self._pg.get_by_path(db=session, file_path=full_old_path)):
                raise EXC(ErrorCode.FileNotExists)
            changes = {}

            if needs_move:
                if not await check_file(full_new_path, session, self._pg, False):
                    raise EXC(ErrorCode.FileAlreadyExists)
                make_directory(target_dir)
                try:
                    await move_file_async(full_old_path, full_new_path)
                    new_base_name, _, new_dir = get_file_parts(full_new_path)
                    changes['path'] = new_dir
                    changes['name'] = new_base_name
                except:
                    raise EXC(ErrorCode.FileMoveError)

            if update_obj.comment is not None and update_obj.comment != db_obj.comment:
                changes['comment'] = update_obj.comment

            changes['updated_at'] = datetime.now(timezone.utc)

            updated_obj = await self._pg.update(db=session, db_obj=db_obj, obj_in=changes)
            return updated_obj.to_public_file(self.base_dir, self._tz.get_current_timezone())

    async def get_file(
        self,
        file_path: str,
        chunk_size: int = 1024,
    ) -> tuple[AsyncGenerator[bytes, None], str]:
        try:
            full_path = secure_path_join(self.base_dir, file_path)
        except:
            raise EXC(ErrorCode.PathUnsafeError)

        async with self._session_provider.get_session() as session:
            if not await check_file(full_path, session, self._pg, True):
                raise EXC(ErrorCode.FileNotExists)

        async def file_generator() -> AsyncGenerator[bytes, None]:
            try:
                async with aiofiles.open(full_path, mode='rb') as f:
                    while True:
                        chunk = await f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
            except:
                raise EXC(ErrorCode.FileDownloadingError)

        base_name, ext, _ = get_file_parts(file_path)
        return file_generator(), f'{base_name}{ext}'

    async def delete_file(self, file_path: str) -> FilePublic:
        try:
            full_path = secure_path_join(self.base_dir, file_path)
        except:
            raise EXC(ErrorCode.PathUnsafeError)

        async with self._session_provider.get_session() as session:
            if not await check_file(full_path, session, self._pg, True):
                raise EXC(ErrorCode.FileNotExists)

            deleted_obj = await self._pg.remove_by_path(db=session, file_path=full_path)

        await asyncio.to_thread(os.remove, full_path)

        return deleted_obj.to_public_file(self.base_dir, self._tz.get_current_timezone())

    async def get_file_info(self, file_path: str) -> FilePublic:
        try:
            file_path = secure_path_join(self.base_dir, file_path)
        except:
            raise EXC(ErrorCode.PathUnsafeError)
        async with self._session_provider.get_session() as session:
            if not (file := await self._pg.get_by_path(db=session, file_path=file_path)):
                raise EXC(ErrorCode.FileNotExists)
        return file.to_public_file(self.base_dir, self._tz.get_current_timezone())

    async def list_dir(self, dir_path: str) -> list[FilePublic]:
        # if dir_path == './' or dir_path == '.':
        #     dir_path = ''
        try:
            dir_path = secure_path_join(self.base_dir, dir_path)
        except:
            raise EXC(ErrorCode.PathUnsafeError)
        async with self._session_provider.get_session() as session:
            files = await self._pg.list_dir(db=session, dir_path=dir_path)

        return [file.to_public_file(self.base_dir, self._tz.get_current_timezone()) for file in files]

    async def list_all_files(
        self,
        skip: int = 0,
        limit: int = 10,
    ) -> list[FilePublic]:
        async with self._session_provider.get_session() as session:
            files = await self._pg.get_multi(db=session, skip=skip, limit=limit)
        return [file.to_public_file(self.base_dir, self._tz.get_current_timezone()) for file in files]
