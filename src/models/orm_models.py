from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Optional
from uuid import UUID

from sqlmodel import Column, DateTime, Field, SQLModel, UniqueConstraint
from ulid import ULID

from src.base_async.base_module.model import BaseOrmMappedModel

SCHEMA_NAME = 'external_modules'


class FileCreate(SQLModel, table=False):
    """."""

    file_path: str
    comment: str | None = ''


class FileUpdate(SQLModel, table=False):
    """Model for updating file fields.
    All fields are optional. If a field is not provided, the corresponding attribute will not be changed.
    """

    name: str | None = Field(default=None)
    new_dir_path: str | None = Field(default=None)
    comment: str | None = Field(default=None)


class FilePublic(SQLModel, table=False):
    """."""

    name: str
    extension: str
    path: str
    size: int
    created_at: str | None
    updated_at: str | None
    comment: str | None


class File(BaseOrmMappedModel, table=True):
    """."""

    id: UUID | None = Field(primary_key=True, index=True, default=ULID.from_timestamp(time.time()).to_uuid())

    name: str = Field(default=None, unique=False, nullable=True)
    extension: str = Field(default=None, unique=False, nullable=False, max_length=13)
    path: str = Field(default=None, unique=False, nullable=True)
    size: int = Field(default=None, unique=False, nullable=True)
    created_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)), default=None)
    updated_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)), default=None)
    comment: str | None = Field(default=None, unique=False, nullable=True)

    # Uniqueness condition to prevent duplicate files in the same folder
    __table_args__ = (
        UniqueConstraint('name', 'extension', 'path', name='uq_name_extension_path'),
        {'schema': SCHEMA_NAME},
    )

    @classmethod
    def from_file_create(cls, file: FileCreate) -> Optional['File']:
        p = Path(file.file_path)

        file_name = p.stem
        extension = p.suffix
        directory = str(p.parent)

        stat_info = p.stat()
        size = stat_info.st_size
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        return File(
            id=ULID.from_timestamp(time.time()).to_uuid(),
            name=file_name,
            extension=extension,
            path=directory,
            size=size,
            created_at=created_at,
            updated_at=updated_at,
            comment=file.comment,
        )

    def to_public_file(self, base_dir: str, current_timezone) -> FilePublic:
        def format_time(dt) -> str | None:
            if dt is None:
                return None
            time = dt.astimezone(current_timezone)
            return time.isoformat()

        return FilePublic(
            name=self.name,
            extension=self.extension,
            # Remove the full path for increased security
            path=self.path.replace(str(Path(base_dir).resolve()), ''),
            size=self.size,
            created_at=format_time(self.created_at),
            updated_at=format_time(self.updated_at),
            comment=self.comment,
        )
