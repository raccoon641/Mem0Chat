from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

import dateparser
import pytz


def now_tz(tz_name: str) -> datetime:
    tz = pytz.timezone(tz_name)
    return datetime.now(tz)


def parse_natural_time_range(text: str, tz_name: str) -> Optional[Tuple[datetime, datetime]]:
    tz = pytz.timezone(tz_name)
    ref = datetime.now(tz)
    settings = {
        "TIMEZONE": tz_name,
        "RETURN_AS_TIMEZONE_AWARE": True,
        "RELATIVE_BASE": ref,
    }
    start = dateparser.parse(text, settings=settings)
    if start is None:
        return None
    end = ref
    if start > end:
        start, end = end, start
    # Normalize to UTC naive to match DB `created_at`
    start_utc = start.astimezone(pytz.UTC).replace(tzinfo=None)
    end_utc = end.astimezone(pytz.UTC).replace(tzinfo=None)
    return start_utc, end_utc 