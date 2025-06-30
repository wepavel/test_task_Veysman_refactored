from datetime import datetime, timezone

import pytz


class TimezoneService:
    """."""

    def __init__(self, timezone: str):
        """."""
        self._current_timezone = pytz.timezone(timezone)

    def get_current_timezone(self):
        return self._current_timezone

    def timezone_to_utc(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            dt = self._current_timezone.localize(dt)
        return dt.astimezone(timezone.utc)
