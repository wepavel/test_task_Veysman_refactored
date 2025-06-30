import os

from sqlmodel import Field
import yaml

from src.base_async.base_module import (
    ExternalPgConfig,
    Model,
)


class ServiceConfig(Model):
    """."""

    pg: ExternalPgConfig = Field()
    storage_dir: str = Field(default=os.getenv('BASE_STORAGE_DIR', 'storage'))
    timezone: str = Field()


config: ServiceConfig = ServiceConfig.load(yaml.safe_load(open(os.getenv('YAML_PATH', 'config.yaml'))) or {})
