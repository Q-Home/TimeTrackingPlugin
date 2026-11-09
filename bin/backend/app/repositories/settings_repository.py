from app.utils.date_helper import DateHelper


class SettingsRepository:
    def __init__(self, mongo):
        self.mongo = mongo

    def get_setting(self, key: str):
        return self.mongo.db["app_settings"].find_one({"key": key})

    def upsert_setting(self, key: str, value: dict):
        now = DateHelper.utc_now()
        return self.mongo.db["app_settings"].update_one(
            {"key": key},
            {
                "$set": {
                    "key": key,
                    "value": value,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "created_at": now,
                },
            },
            upsert=True,
        )

    def create_indexes(self):
        self.mongo.db["app_settings"].create_index("key", unique=True)
