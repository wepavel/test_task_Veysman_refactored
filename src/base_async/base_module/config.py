import os

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

    host: str = Field(default=os.getenv('STORAGES_PGSQL_HOST'))
    port: int = Field(default=int(os.getenv('STORAGES_PGSQL_PORT', 5432)))
    user: str = Field(default=os.getenv('STORAGES_PGSQL_USER'))
    password: str = Field(default=os.getenv('STORAGES_PGSQL_PASS'))
    database: str = Field(default=os.getenv('STORAGES_PGSQL_ORBISMAP_DB'))
    schema: str = Field(default='external_modules')
