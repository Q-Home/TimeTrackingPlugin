from bson.objectid import ObjectId
from datetime import datetime, timedelta


class BadgeRepository:
    def __init__(self, mongo):
        self.mongo = mongo

    def aggregate_users_from_badges(self, pipeline):
        return self.mongo.db["badge_logs"].aggregate(pipeline)

    def count_badges(self, query):
        return self.mongo.db["badge_logs"].count_documents(query)

    def find_badges(self, query, skip=0, limit=50):
        return (
            self.mongo.db["badge_logs"]
            .find(query)
            .sort("timestamp", -1)
            .skip(skip)
            .limit(limit)
        )

    def find_badge_by_id(self, badge_id: str):
        return self.mongo.db["badge_logs"].find_one({"_id": ObjectId(badge_id)})

    def insert_badge(self, badge_data: dict):
        return self.mongo.db["badge_logs"].insert_one(badge_data)

    def update_badge(self, badge_id: str, update_fields: dict):
        return self.mongo.db["badge_logs"].update_one(
            {"_id": ObjectId(badge_id)},
            {"$set": update_fields}
        )

    def delete_badge(self, badge_id: str):
        return self.mongo.db["badge_logs"].delete_one({"_id": ObjectId(badge_id)})

    def bulk_mark_processed(self, object_ids, update_fields):
        return self.mongo.db["badge_logs"].update_many(
            {"_id": {"$in": object_ids}},
            {"$set": update_fields}
        )

    def find_badges_for_user_and_day(self, username: str, day: datetime):
        start_of_day = datetime(day.year, day.month, day.day, 0, 0, 0, 0)
        end_of_day = start_of_day + timedelta(days=1)

        return list(
            self.mongo.db["badge_logs"]
            .find({
                "username": username,
                "timestamp": {
                    "$gte": start_of_day,
                    "$lt": end_of_day
                }
            })
            .sort("timestamp", 1)
        )

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

    def create_indexes(self):
        self.mongo.db["badge_logs"].create_index("timestamp")
        self.mongo.db["badge_logs"].create_index("badge_code")
        self.mongo.db["badge_logs"].create_index("username")
        self.mongo.db["badge_logs"].create_index("user_id")