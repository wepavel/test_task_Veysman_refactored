from src.base_async.injectors import AsyncPgConnectionInj
from src.config import config

pg = AsyncPgConnectionInj(
    conf=config.pg,
)
