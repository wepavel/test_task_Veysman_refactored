from __future__ import annotations

import abc
from collections.abc import Generator
from enum import Enum
from typing import Any, ClassVar, Generic, TypeVar

from pydantic import ConfigDict, model_validator
from sqlmodel import SQLModel

from .exception import ModuleException


class ModelException(ModuleException):
    """."""

    prefix: str = 'ошибка обработки модели'


class ValuedEnum(str, Enum):
    """."""

    @classmethod
    def has_value(cls, value: Any) -> bool:
        return value in cls._value2member_map_

    @classmethod
    def values(cls) -> list[Any]:
        return list(cls._value2member_map_.keys())

    @classmethod
    def from_key(cls, key: str, safe: bool = True) -> ValuedEnum | None:
        member = cls.__members__.get(key)
        if member is None and not safe:
            raise ModelException(msg=f'Недопустимое значение: {key}', code=400)
        return member

    @classmethod
    def from_value(cls, value: Any, safe: bool = True) -> ValuedEnum | None:
        for m in cls._value2member_map_.values():
            if m.value == value:
                return m
        if not safe:
            raise ModelException(msg=f'Недопустимое значение: {value}', code=400)
        return None

    @classmethod
    def from_name(cls, name: str):
        return cls._member_map_[name]

    @classmethod
    def to_dict(cls) -> dict[str, Any]:
        return {k: v.value for k, v in cls.__members__.items()}


TV_MODEL = TypeVar('TV_MODEL', bound='Model')


class Model(SQLModel, table=False):
    """."""

    model_config = ConfigDict(
        populate_by_name=True,
        validate_default=True,
        extra='forbid',
        from_attributes=True,
    )

    @classmethod
    def load(cls: type[TV_MODEL], data: Any) -> TV_MODEL:
        try:
            if isinstance(data, cls):
                return data
            return cls.model_validate(data)
        except Exception as e:
            raise ModelException(
                msg=f'Ошибка загрузки модели {cls.__name__}', data={'e': str(e), 'model': cls.__name__}
            ) from e

    def dump(self) -> dict[str, Any]:
        return self.model_dump()

    def update(self, data: dict[str, Any]) -> None:
        patched = self.model_copy(update=data)
        # перезаписываем self-поля
        for k, v in patched.model_dump().items():
            object.__setattr__(self, k, v)

    def reload(self) -> TV_MODEL:
        return self.load(self.dump())

    def validate(self) -> None:
        self.model_validate(self.dump())


def view(cls: type[Model]):
    field_names = list(cls.model_fields)

    def _view(model: Model) -> dict[str, Any]:
        data = model.dump() if isinstance(model, Model) else dict(model)
        return {k: data[k] for k in field_names if k in data}

    return _view


class BaseOrmMappedModel(Model):
    """."""

    model_config = ConfigDict(
        from_attributes=True,
        extra='ignore',
    )


MT = TypeVar('MT', bound=Model)


class MetaModel(Model, Generic[MT], abc.ABC):
    """."""

    __key__: ClassVar[str]

    @model_validator(mode='after')
    def _load_metadata(self) -> MetaModel[MT]:
        for name, field in self.model_fields.items():
            meta_info = field.metadata.get(self.__key__)
            if meta_info is not None:
                raw = getattr(self, name)
                # если передан словарь — парсим его, иначе оставляем как есть
                obj: MT = meta_info.load(raw) if isinstance(raw, dict) else raw
                object.__setattr__(self, name, obj)
        return self

    def iterate_metadata(self) -> Generator[tuple[str, MT], None, None]:
        for name, field in self.model_fields.items():
            meta_info = field.metadata.get(self.__key__)
            if meta_info:
                yield name, getattr(self, name)
