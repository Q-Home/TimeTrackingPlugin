from datetime import datetime, timedelta

from app.models.badge import Badge
from app.utils.response import success_response, error_response


class DashboardService:
    PRESENT_ACTIONS = {"START", "RETURN", "BREAK", "SCAN_IN"}
    BREAK_ACTIONS = {"BREAK"}
    EXIT_ACTIONS = {"STOP", "SCAN_OUT"}

    def __init__(self, badge_repository, user_repository, timesheet_service, log_repository):
        self.badge_repository = badge_repository
        self.user_repository = user_repository
        self.timesheet_service = timesheet_service
        self.log_repository = log_repository

    def get_admin_summary(self):
        try:
            now = datetime.now()
            start_of_today = datetime(now.year, now.month, now.day, 0, 0, 0, 0)
            end_of_today = datetime(now.year, now.month, now.day, 23, 59, 59, 999999)
            last_hour = now - timedelta(hours=1)

            today_logs = self.badge_repository.find_badges_in_range(start_of_today, end_of_today)
            recent_logs = self.badge_repository.find_recent_badges(limit=8)
            users = self.user_repository.find_all()

            users_by_username = {
                (user.get("username") or ""): user
                for user in users
                if user.get("username")
            }

            grouped_logs = {}
            for log_doc in today_logs:
                badge = Badge.from_mongo(log_doc)
                username = badge.username or ""
                if not username:
                    continue
                grouped_logs.setdefault(username, []).append(log_doc)

            presence_people = []
            on_break_count = 0
            active_today_count = 0
            scans_last_hour = sum(
                1
                for log_doc in today_logs
                if Badge.from_mongo(log_doc).timestamp and Badge.from_mongo(log_doc).timestamp >= last_hour
            )

            for username, user_logs in grouped_logs.items():
                if not user_logs:
                    continue

                active_today_count += 1

                latest_badge = Badge.from_mongo(user_logs[-1])
                latest_action = self.timesheet_service._normalize_action(latest_badge.action)
                current_status = self._presence_status(latest_action)

                if current_status == "away":
                    continue

                if current_status == "on_break":
                    on_break_count += 1

                user_doc = users_by_username.get(username, {})
                presence_people.append({
                    "username": username,
                    "display_name": self._display_name(user_doc, latest_badge),
                    "first_name": user_doc.get("first_name") or latest_badge.first_name or "",
                    "last_name": user_doc.get("last_name") or latest_badge.last_name or "",
                    "company_name": user_doc.get("company_name", ""),
                    "status": current_status,
                    "last_action": latest_action,
                    "last_seen": latest_badge.timestamp.isoformat() if latest_badge.timestamp else None,
                    "location": latest_badge.location or "",
                    "device_id": latest_badge.device_id or "",
                })

            presence_people.sort(key=lambda person: person.get("last_seen") or "", reverse=True)

            location_summary = {}
            for person in presence_people:
                location = person.get("location") or "Onbekende locatie"
                location_summary[location] = location_summary.get(location, 0) + 1

            locations = [
                {"location": location, "count": count}
                for location, count in sorted(location_summary.items(), key=lambda item: (-item[1], item[0]))
            ]

            recent_activity = []
            for log_doc in recent_logs:
                badge = Badge.from_mongo(log_doc)
                user_doc = users_by_username.get(badge.username or "", {})
                recent_activity.append({
                    "username": badge.username,
                    "display_name": self._display_name(user_doc, badge),
                    "action": self.timesheet_service._normalize_action(badge.action),
                    "timestamp": badge.timestamp.isoformat() if badge.timestamp else None,
                    "location": badge.location or "",
                    "device_id": badge.device_id or "",
                })

            total_user_count = len(users_by_username)
            present_count = len(presence_people)
            occupancy_rate = round((present_count / total_user_count) * 100, 1) if total_user_count else 0
            starts_today = sum(
                1 for log_doc in today_logs
                if self.timesheet_service._normalize_action(Badge.from_mongo(log_doc).action) in {"START", "SCAN_IN"}
            )
            stops_today = sum(
                1 for log_doc in today_logs
                if self.timesheet_service._normalize_action(Badge.from_mongo(log_doc).action) in {"STOP", "SCAN_OUT"}
            )

            return success_response({
                "stats": {
                    "present_now": present_count,
                    "on_break_now": on_break_count,
                    "active_today": active_today_count,
                    "total_users": total_user_count,
                    "occupancy_rate": occupancy_rate,
                    "scans_today": len(today_logs),
                    "starts_today": starts_today,
                    "stops_today": stops_today,
                    "scans_last_hour": scans_last_hour,
                },
                "people_in_building": presence_people[:8],
                "locations": locations[:6],
                "recent_activity": recent_activity,
            }, "Dashboard summary retrieved successfully")
        except Exception as exc:
            self.log_repository.error(f"Error building dashboard summary: {exc}")
            return error_response("Failed to build dashboard summary", 500)

    def _presence_status(self, latest_action):
        if latest_action in self.BREAK_ACTIONS:
            return "on_break"
        if latest_action in self.PRESENT_ACTIONS:
            return "present"
        if latest_action in self.EXIT_ACTIONS:
            return "away"
        return "away"

    def _display_name(self, user_doc, badge):
        first_name = user_doc.get("first_name") or badge.first_name or ""
        last_name = user_doc.get("last_name") or badge.last_name or ""
        full_name = f"{first_name} {last_name}".strip()
        return full_name or user_doc.get("username") or badge.username or "Onbekend"
