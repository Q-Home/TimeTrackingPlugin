from app.utils.response import error_response


class AuthValidator:
    @staticmethod
    def validate_login(data):
        username = data.get("username")
        password = data.get("password")

        if not username or not password:
            return error_response("Username and password are required", 400)

        return None