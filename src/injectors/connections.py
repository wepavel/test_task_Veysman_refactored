from src.base_async.injectors import AsyncPgConnectionInj
from src.config import config
from src.models import *  # noqa


pg = AsyncPgConnectionInj(
    conf=config.pg,
)
