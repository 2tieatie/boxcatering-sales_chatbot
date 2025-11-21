from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from datetime import date

def format_kyiv_timestamp(ts) -> str:
    if isinstance(ts, datetime):
        dt = ts
    elif isinstance(ts, str):
        try:
            dt = datetime.fromisoformat(ts)
        except ValueError:
            raise
    else:
        raise TypeError("ts must be str or datetime")

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    kyiv_time = dt.astimezone(ZoneInfo("Europe/Kyiv"))
    return kyiv_time.strftime("%d.%m.%Y %H:%M")


def parse_delivery_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(
            value.year, value.month, value.day, tzinfo=timezone.utc
        )
    if isinstance(value, str):
        value = value.strip()
        for fmt in ("%Y-%m-%d", "%Y.%m.%d"):
            try:
                dt = datetime.strptime(value, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
        for fmt in ("%d.%m.%Y", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(value, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def parse_bool(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).lower().strip()
    return s in {"1", "true", "yes", "on"}