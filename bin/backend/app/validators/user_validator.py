import re
from app.utils.response import error_response
from app.constants.roles import Roles


class UserValidator:
    @staticmethod
    def validate_create_user(data):
        username = data.get("username")
        email = data.get("email")
        password = data.get("password")
        role = data.get("role", "user")

        if not username or len(username) < 3:
            return error_response("Username must be at least 3 characters", 400)

        if not email:
            return error_response("Email is required", 400)

        email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(email_regex, email):
            return error_response("Invalid email address", 400)

        if not password or len(password) < 6:
            return error_response("Password must be at least 6 characters", 400)

        if role not in Roles.ALL:
            return error_response("Invalid role", 400)

        return None