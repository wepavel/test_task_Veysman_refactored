import os
import yaml

from pydantic import (
    BaseModel,
    # BaseSettings,
    Field,
    PostgresDsn,
    root_validator,
    field_validator,
)
from src.base_async.base_module import (
    # LoggerConfig,
    # OMSPgConfig,
    ExternalPgConfig,
    Model,
    # OMSSetupConfig
)


class ServiceConfig(Model):
    """."""

    # rabbit: RabbitFullConfig = dc.field()
    # oms: OMSModulesConfig = dc.field(default=OMSModulesConfig())
    pg: ExternalPgConfig = Field()
    storage_dir: str = Field(default='/storage')
    # tmp_dir: str = Field(default='/tmp')
    # static_dir: str = Field(default='/static')
    # config_data: SetupConfig = Field(default=SetupConfig())
    # logging: LoggerConfig | None = Field(default=None)


config: ServiceConfig = ServiceConfig.load(
    yaml.safe_load(open(os.getenv('YAML_PATH', "config.yaml"))) or {}
)
