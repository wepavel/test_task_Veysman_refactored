from typing import Any

from ..base_module.model import Model


class BaseOrmModel(Model):
    """."""

    id: Any
    __name__: str

    # Generate __tablename__ automatically
    @classmethod
    @property
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
