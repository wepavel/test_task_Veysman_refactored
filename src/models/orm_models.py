from src.base_async.base_module.model import BaseOrmMappedModel
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import UUID

from sqlmodel import Column
from sqlmodel import DateTime
from sqlmodel import Field
from sqlmodel import SQLModel
from sqlmodel import UniqueConstraint
from ulid import ULID

# from src.core.config import settings
# from src.core.utils import current_timezone
# from src.core.utils import timezone
# from src.db.base_class import Base

SCHEMA_NAME = 'external_modules'

class File(BaseOrmMappedModel, table=True):
    id: UUID | None = Field(primary_key=True, index=True, default=ULID.from_timestamp(time.time()).to_uuid())

    name: str = Field(default=None, unique=False, nullable=True)
    extension: str = Field(default=None, unique=False, nullable=False, max_length=13)
    path: str = Field(default=None, unique=False, nullable=True)
    size: int = Field(default=None, unique=False, nullable=True)
    created_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)), default=None)
    updated_at: datetime | None = Field(sa_column=Column(DateTime(timezone=True)), default=None)
    comment: str | None = Field(default=None, unique=False, nullable=True)

    # Uniqueness condition to prevent duplicate files in the same folder
    __table_args__ = (UniqueConstraint('name', 'extension', 'path', name='uq_name_extension_path'),
                      {'schema': SCHEMA_NAME}
                      )