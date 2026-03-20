from datetime import datetime, timedelta


def find_badges_for_user_and_range(self, username: str, start_date: datetime, end_date: datetime):
    return list(
        self.mongo.db["badge_logs"]
        .find({
            "username": username,
            "timestamp": {
                "$gte": start_date,
                "$lte": end_date
            }
        })
        .sort("timestamp", 1)
    )