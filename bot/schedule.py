import zoneinfo
from datetime import date, datetime, time as dt_time, timedelta


def get_run_time(config: dict) -> dt_time:
    schedule = config["schedule"]
    hour, minute = map(int, schedule["time"].split(":"))
    tz = zoneinfo.ZoneInfo(schedule["timezone"])
    return dt_time(hour=hour, minute=minute, tzinfo=tz)


def next_week_range(timezone: str, days: int) -> tuple[date, date]:
    tz = zoneinfo.ZoneInfo(timezone)
    today = datetime.now(tz).date()
    end = today + timedelta(days=days)
    return today, end
