from datetime import datetime


class TimesheetService:
    VALID_ACTIONS = {"START", "STOP", "BREAK", "RETURN"}

    def calculate_day_timesheet(self, badge_logs):
        """
        badge_logs must be sorted by timestamp ascending
        """
        work_seconds = 0
        break_seconds = 0

        work_start = None
        break_start = None
        status = "idle"  # idle, working, on_break

        events = []
        errors = []

        for log in badge_logs:
            action = (log.get("action") or "").upper()
            timestamp = log.get("timestamp")

            if not action or action not in self.VALID_ACTIONS:
                errors.append(f"Invalid action: {action}")
                continue

            if not isinstance(timestamp, datetime):
                errors.append(f"Invalid timestamp for action {action}")
                continue

            events.append({
                "action": action,
                "timestamp": timestamp.isoformat()
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
                    break_start = timestamp
                    work_start = None
                    status = "on_break"
                else:
                    errors.append(f"Unexpected BREAK at {timestamp.isoformat()} while status={status}")

            elif action == "RETURN":
                if status == "on_break" and break_start:
                    break_seconds += (timestamp - break_start).total_seconds()
                    work_start = timestamp
                    break_start = None
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