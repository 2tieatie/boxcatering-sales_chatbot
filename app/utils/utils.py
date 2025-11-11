from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def format_kyiv_timestamp(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
    except ValueError:
        raise

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    kyiv_time = dt.astimezone(ZoneInfo("Europe/Kyiv"))

    return kyiv_time.strftime("%d.%m.%Y %H:%M")
