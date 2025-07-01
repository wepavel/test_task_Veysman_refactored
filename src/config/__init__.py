import os

import yaml
from sqlmodel import Field

from src.base_async.base_module import (
    ExternalPgConfig,
    Model,
)


class FileConfig(Model):
    """."""

    upload_chunk_size: int = Field(default=1024 * 1024 * 5)  # 5 MB


class ServiceConfig(Model):
    """."""

    pg: ExternalPgConfig = Field()
    storage_dir: str = Field(default='storage')
    timezone: str = Field()
    file_config: FileConfig = Field(default=FileConfig())


config: ServiceConfig = ServiceConfig.load(yaml.safe_load(open(os.getenv('YAML_PATH', 'config.yaml'))) or {})
