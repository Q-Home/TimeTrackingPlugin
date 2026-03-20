from datetime import datetime, timedelta
from app.models.badge import Badge


class TimesheetService:
    VALID_ACTIONS = {"START", "STOP", "BREAK", "RETURN"}

    def __init__(self, badge_repository):
        self.badge_repository = badge_repository

    def calculate_day_timesheet(self, badge_logs):
        work_seconds = 0
        break_seconds = 0

        work_start = None
        break_start = None
        status = "idle"

        events = []
        errors = []

        for log_doc in badge_logs:
            badge = Badge.from_mongo(log_doc)
            action = badge.action
            timestamp = badge.timestamp

            if action not in self.VALID_ACTIONS:
                continue

            if not isinstance(timestamp, datetime):
                errors.append(f"Invalid timestamp for action {action}")
                continue

            events.append({
                "action": action,
                "timestamp": timestamp.isoformat(),
                "badge_code": badge.badge_code,
                "username": badge.username,
            })

            if action == "START":
                if status == "idle":
                    work_start = timestamp
                    status = "working"
                else:
                    errors.append(f"Unexpected START at {timestamp.isoformat()} while status={status}")

            elif action == "BREAK":
                if status == "working" and work_start:
                    work_seconds += (timestamp - work_start).total_seconds()
                    work_start = None
                    break_start = timestamp
                    status = "on_break"
                else:
                    errors.append(f"Unexpected BREAK at {timestamp.isoformat()} while status={status}")

            elif action == "RETURN":
                if status == "on_break" and break_start:
                    break_seconds += (timestamp - break_start).total_seconds()
                    break_start = None
                    work_start = timestamp
                    status = "working"
                else:
                    errors.append(f"Unexpected RETURN at {timestamp.isoformat()} while status={status}")

            elif action == "STOP":
                if status == "working" and work_start:
                    work_seconds += (timestamp - work_start).total_seconds()
                    work_start = None
                    status = "idle"
                elif status == "on_break" and break_start:
                    break_seconds += (timestamp - break_start).total_seconds()
                    break_start = None
                    status = "idle"
                    errors.append(f"STOP received while on break at {timestamp.isoformat()}")
                else:
                    errors.append(f"Unexpected STOP at {timestamp.isoformat()} while status={status}")

        return {
            "events": events,
            "work_seconds": int(work_seconds),
            "break_seconds": int(break_seconds),
            "net_work_seconds": int(work_seconds),
            "work_hours_decimal": round(work_seconds / 3600, 2),
            "break_hours_decimal": round(break_seconds / 3600, 2),
            "open_status": status,
            "is_complete": status == "idle",
            "errors": errors
        }

    def get_user_timesheet_for_day(self, username: str, day: datetime):
        start_of_day = datetime(day.year, day.month, day.day, 0, 0, 0, 0)
        end_of_day = datetime(day.year, day.month, day.day, 23, 59, 59, 999999)

        logs = self.badge_repository.find_badges_for_user_and_range(
            username=username,
            start_date=start_of_day,
            end_date=end_of_day
        )

        result = self.calculate_day_timesheet(logs)

        return {
            "username": username,
            "date": day.strftime("%Y-%m-%d"),
            "total_logs": len(logs),
            **result
        }

    def get_user_timesheet_for_range(self, username: str, start_date: datetime, end_date: datetime):
        logs = self.badge_repository.find_badges_for_user_and_range(
            username=username,
            start_date=start_date,
            end_date=end_date
        )

        grouped_by_day = {}

        for log_doc in logs:
            badge = Badge.from_mongo(log_doc)
            if not badge.timestamp:
                continue

            date_key = badge.timestamp.strftime("%Y-%m-%d")

            if date_key not in grouped_by_day:
                grouped_by_day[date_key] = []

            grouped_by_day[date_key].append(log_doc)

        days = []
        current_day = start_date.date()
        end_day = end_date.date()

        while current_day <= end_day:
            date_key = current_day.strftime("%Y-%m-%d")
            day_logs = grouped_by_day.get(date_key, [])
            result = self.calculate_day_timesheet(day_logs)

            days.append({
                "username": username,
                "date": date_key,
                "total_logs": len(day_logs),
                **result
            })

            current_day += timedelta(days=1)

        total_work_seconds = sum(day["work_seconds"] for day in days)
        total_break_seconds = sum(day["break_seconds"] for day in days)
        complete_days = sum(1 for day in days if day["is_complete"] and day["work_seconds"] > 0)
        worked_days = sum(1 for day in days if day["work_seconds"] > 0)

        return {
            "username": username,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "days": days,
            "summary": {
                "total_days": len(days),
                "worked_days": worked_days,
                "complete_days": complete_days,
                "total_work_seconds": int(total_work_seconds),
                "total_break_seconds": int(total_break_seconds),
                "total_work_hours_decimal": round(total_work_seconds / 3600, 2),
                "total_break_hours_decimal": round(total_break_seconds / 3600, 2),
                "average_work_hours_per_worked_day": round((total_work_seconds / 3600) / worked_days, 2) if worked_days > 0 else 0
            }
        }