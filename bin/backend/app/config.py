import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change_me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change_me_too")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", "12"))
    )

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/timetracking")
    API_PREFIX = "/api/v1"
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    PORT = int(os.getenv("PORT", "5000"))

    DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin")

    @staticmethod
    def get_cors_origins():
        origins = os.getenv("CORS_ORIGINS", "*")
        if origins == "*":
            return "*"
        return [origin.strip() for origin in origins.split(",")]