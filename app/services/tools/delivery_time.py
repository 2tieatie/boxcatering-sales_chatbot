import json
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from langchain.tools import tool

KYIV = ZoneInfo("Europe/Kyiv")

FORMATS = [
    "%Y-%m-%d %H:%M",
    "%H:%M %Y-%m-%d",
    "%H:%M %d-%m-%Y",
    "%d-%m-%Y %H:%M",
    "%Y.%m.%d %H:%M",
    "%H:%M %Y.%m.%d",
    "%H:%M %d.%m.%Y",
    "%d.%m.%Y %H:%M",
]


def parse_input(input_str: str) -> datetime:
    s = " ".join(input_str.split())
    for fmt in FORMATS:
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=KYIV)
        except ValueError:
            continue
    raise ValueError(f"Unsupported datetime format: {input_str}")


def is_within_working_hours(dt: datetime) -> bool:
    return 9 <= dt.hour <= 19


def validate_delivery(input_str: str) -> dict:
    MIN_PREP_MINUTES = 120
    now = datetime.now(KYIV)
    requested_dt = parse_input(input_str)
    min_ready_dt = now + timedelta(minutes=MIN_PREP_MINUTES)

    if requested_dt < min_ready_dt:
        return {"valid": False, "reason": "Requested time is outside working hours"}

    if not is_within_working_hours(requested_dt):
        return {"valid": False, "reason": "Requested time is outside working hours"}

    minutes_until_delivery = int((requested_dt - now).total_seconds() // 60)
    if minutes_until_delivery < MIN_PREP_MINUTES:
        return {"valid": False, "reason": "Not enough time for preparation"}

    return {
        "valid": True,
        "approved_date": requested_dt.strftime("%Y-%m-%d"),
        "approved_time": requested_dt.strftime("%H:%M"),
    }



@tool
async def validate_time_tool(date: str) -> str:
    """
    Validates delivery time
    Args:
     date (str): date in format YYYY-MM-DD HH:MM
    Returns:
        str: is delivery time valid and formatted date with time
    """
    return json.dumps(validate_delivery(date))


if __name__ == "__main__":
    res = validate_delivery("2025-11-26 15:00")
    print(res)
