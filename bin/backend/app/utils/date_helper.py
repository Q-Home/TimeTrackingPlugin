from datetime import datetime
import pytz


class DateHelper:
    BELGIUM_TZ = pytz.timezone("Europe/Brussels")

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
        belgium = DateHelper.BELGIUM_TZ
        dt_utc = dt.replace(tzinfo=utc) if dt.tzinfo is None else dt.astimezone(utc)
        return dt_utc.astimezone(belgium)

    @staticmethod
    def to_belgian_iso(dt):
        belgian = DateHelper.to_belgian_time(dt)
        if isinstance(belgian, datetime):
            return belgian.isoformat()
        return belgian

    @staticmethod
    def to_utc_naive(value):
        if not value:
            return None

        if isinstance(value, str):
            value = DateHelper.parse_iso_date(value)

        if not isinstance(value, datetime):
            return value

        if value.tzinfo is None:
            return value

        return value.astimezone(pytz.utc).replace(tzinfo=None)

    @staticmethod
    def belgian_day_bounds_to_utc_naive(day: datetime):
        local_start = DateHelper.BELGIUM_TZ.localize(
            datetime(day.year, day.month, day.day, 0, 0, 0, 0)
        )
        local_end = DateHelper.BELGIUM_TZ.localize(
            datetime(day.year, day.month, day.day, 23, 59, 59, 999999)
        )
        return (
            DateHelper.to_utc_naive(local_start),
            DateHelper.to_utc_naive(local_end),
        )
