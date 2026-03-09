from app.utils.date_helper import DateHelper


class LogRepository:
    def __init__(self, mongo):
        self.mongo = mongo

    def insert_log(self, message: str, log_type: str):
        self.mongo.db["logs"].insert_one({
            "message": message,
            "type": log_type,
            "timestamp": DateHelper.utc_now()
        })

    def info(self, message: str):
        self.insert_log(message, "Info")

    def warning(self, message: str):
        self.insert_log(message, "Warning")

    def error(self, message: str):
        self.insert_log(message, "Error")