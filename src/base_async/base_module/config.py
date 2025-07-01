from sqlmodel import Field

from .model import Model


class PgConfig(Model):
    """."""

    host: str = Field()
    port: int = Field()
    user: str = Field()
    password: str = Field()
    database: str = Field()
    max_pool_connections: int = Field(default=100)
    debug: bool = Field(default=False)
    schema: str = Field(default='public')


class ExternalPgConfig(PgConfig):
    """."""

    host: str = Field()
    port: int = Field()
    user: str = Field()
    password: str = Field()
    database: str = Field()
    schema: str = Field(default='external_modules')
