from flask_login import UserMixin


class User(UserMixin):
    def __init__(
        self,
        username: str,
        role: str = "user",
        user_id: str | None = None,
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        company_name: str = "",
        badge_codes: list[str] | None = None,
        blocked: bool = False,
        total_scans: int = 0,
        first_activity=None,
        last_activity=None,
    ):
        self.username = username
        self.role = role
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.email = email
        self.company_name = company_name
        self.badge_codes = badge_codes or []
        self.blocked = blocked
        self.total_scans = total_scans
        self.first_activity = first_activity
        self.last_activity = last_activity
        self.authenticated = True

    def get_id(self):
        return self.username

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "role": self.role,
            "user_id": self.user_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": self.full_name,
            "email": self.email,
            "company_name": self.company_name,
            "badge_codes": self.badge_codes,
            "blocked": self.blocked,
            "total_scans": self.total_scans,
            "first_activity": self.first_activity,
            "last_activity": self.last_activity,
        }

    @classmethod
    def from_mongo(cls, data: dict):
        return cls(
            username=data.get("username", ""),
            role=data.get("role", data.get("user_role", "user")),
            user_id=str(data.get("_id")) if data.get("_id") else data.get("user_id"),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            email=data.get("email", ""),
            company_name=data.get("company_name", ""),
            badge_codes=data.get("badge_codes", []),
            blocked=data.get("blocked", False),
            total_scans=data.get("total_scans", 0),
            first_activity=data.get("first_activity"),
            last_activity=data.get("last_activity"),
        )

    @classmethod
    def from_aggregation(cls, data: dict):
        return cls(
            username=data.get("username", ""),
            role=data.get("role", data.get("user_role", "user")),
            user_id=data.get("user_id"),
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            email=data.get("email", ""),
            company_name=data.get("company_name", ""),
            badge_codes=data.get("badge_codes", []),
            blocked=data.get("blocked", False),
            total_scans=data.get("total_scans", 0),
            first_activity=data.get("first_activity"),
            last_activity=data.get("last_activity"),
        )