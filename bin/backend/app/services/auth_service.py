import bcrypt
from pymongo.errors import DuplicateKeyError
from flask_jwt_extended import create_access_token
from app.config import Config
from app.utils.response import success_response, error_response
from app.validators.auth_validator import AuthValidator
from app.constants.roles import Roles


class AuthService:
    def __init__(self, user_repository, log_repository):
        self.user_repository = user_repository
        self.log_repository = log_repository

    def login(self, data):
        validation = AuthValidator.validate_login(data)
        if validation:
            return validation

        username_or_email = data.get("username")
        password = data.get("password")

        user = self.user_repository.find_by_username_or_email(username_or_email)
        if not user:
            return error_response("Invalid login credentials", 401)

        if user.get("blocked", False):
            return error_response("Account is blocked", 403)

        if not bcrypt.checkpw(password.encode("utf-8"), user["password"].encode("utf-8")):
            return error_response("Invalid login credentials", 401)

        access_token = create_access_token(
            identity=user["username"],
            additional_claims={
                "role": user.get("role", Roles.USER),
                "email": user.get("email", "")
            }
        )

        self.log_repository.info(f"User logged in: {user['username']}")

        return success_response({
            "access_token": access_token,
            "token_type": "Bearer",
            "username": user["username"],
            "role": user.get("role", Roles.USER)
        }, "Login successful", 200)

    def create_default_admin(self):
        try:
            username = Config.DEFAULT_ADMIN_USERNAME
            password = Config.DEFAULT_ADMIN_PASSWORD

            hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

            result = self.user_repository.create_default_admin_if_missing({
                "username": username,
                "first_name": "Administrator",
                "last_name": "User",
                "email": "admin@timetracking.local",
                "company_name": "TimeTracking System",
                "password": hashed_pw.decode("utf-8"),
                "role": Roles.ADMIN,
                "blocked": False
            })

            if result.upserted_id:
                self.log_repository.info("Default admin user created")
            else:
                self.log_repository.info("Default admin user already exists")

        except DuplicateKeyError:
            self.log_repository.info("Default admin already created by another worker")
        except Exception as e:
            self.log_repository.error(f"Error creating default admin: {e}")