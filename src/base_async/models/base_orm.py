from typing import Any

from ..base_module.model import BaseOrmMappedModel


class BaseOrmModel(BaseOrmMappedModel):
    """."""

    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @classmethod
    @property
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
