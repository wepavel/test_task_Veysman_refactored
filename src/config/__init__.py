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
    storage_dir: str = Field(default='storage')
    timezone: str = Field()
    upload_chunk_size: int = Field(default=1024 * 1024 * 5)  # 5 MB
    upload_file_max_size: int = Field(default=100 * 1024 * 1024)  # 100 MB


config: ServiceConfig = ServiceConfig.load(yaml.safe_load(open(os.getenv('YAML_PATH', 'config.yaml'))) or {})
