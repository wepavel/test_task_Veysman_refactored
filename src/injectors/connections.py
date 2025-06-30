from src.base_async.injectors import AsyncPgConnectionInj
from src.config import config
from src.models import *

pg = AsyncPgConnectionInj(
    conf=config.pg,
)
