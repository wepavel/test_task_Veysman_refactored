from datetime import datetime
from datetime import timezone

import pytz

current_timezone = pytz.timezone('Europe/Moscow')


def timezone_to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = current_timezone.localize(dt)
    return dt.astimezone(timezone.utc)