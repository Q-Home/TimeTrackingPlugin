from datetime import datetime
import pytz


class DateHelper:
    @staticmethod
    def utc_now():
        return datetime.utcnow()

    @staticmethod
    def to_iso(value):
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @staticmethod
    def parse_iso_date(value: str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def to_belgian_time(dt):
        if not dt:
            return None

        if isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            except Exception:
                return dt

        if not isinstance(dt, datetime):
            return dt

        utc = pytz.utc
        belgium = pytz.timezone("Europe/Brussels")
        dt_utc = dt.replace(tzinfo=utc) if dt.tzinfo is None else dt.astimezone(utc)
        return dt_utc.astimezone(belgium)