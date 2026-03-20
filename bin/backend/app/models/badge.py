from datetime import datetime


class Badge:
    VALID_ACTIONS = {"START", "STOP", "BREAK", "RETURN", "SCAN", "SCAN_IN", "SCAN_OUT"}

    def __init__(
        self,
        badge_code: str,
        action: str,
        username: str = "",
        user_id: str = "",
        first_name: str = "",
        last_name: str = "",
        location: str = "",
        device_id: str = "",
        raw_data: dict | None = None,
        processed: bool = False,
        timestamp: datetime | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        badge_id: str | None = None,
    ):
        normalized_action = (action or "SCAN").upper()

        if normalized_action not in self.VALID_ACTIONS:
            raise ValueError(f"Invalid badge action: {normalized_action}")

        self.id = badge_id
        self.badge_code = badge_code
        self.action = normalized_action
        self.username = username
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.location = location
        self.device_id = device_id
        self.raw_data = raw_data or {}
        self.processed = processed
        self.timestamp = timestamp or datetime.utcnow()
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def to_mongo_dict(self) -> dict:
        return {
            "badge_code": self.badge_code,
            "action": self.action,
            "username": self.username,
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "location": self.location,
            "device_id": self.device_id,
            "raw_data": self.raw_data,
            "processed": self.processed,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "badge_code": self.badge_code,
            "action": self.action,
            "username": self.username,
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "location": self.location,
            "device_id": self.device_id,
            "raw_data": self.raw_data,
            "processed": self.processed,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_mongo(cls, data: dict):
        return cls(
            badge_id=str(data.get("_id")) if data.get("_id") else None,
            badge_code=data.get("badge_code", ""),
            action=data.get("action", "SCAN"),
            username=data.get("username", ""),
            user_id=data.get("user_id", ""),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            location=data.get("location", ""),
            device_id=data.get("device_id", ""),
            raw_data=data.get("raw_data", {}),
            processed=data.get("processed", False),
            timestamp=data.get("timestamp"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )