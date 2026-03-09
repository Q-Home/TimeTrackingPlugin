import bcrypt
from app.validators.user_validator import UserValidator
from app.utils.response import success_response, error_response
from app.utils.date_helper import DateHelper


class UserService:
    def __init__(self, user_repository, badge_repository, log_repository):
        self.user_repository = user_repository
        self.badge_repository = badge_repository
        self.log_repository = log_repository

    def get_users(self):
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": "$username",
                        "username": {"$first": "$username"},
                        "user_id": {"$first": "$user_id"},
                        "first_name": {"$first": "$first_name"},
                        "last_name": {"$first": "$last_name"},
                        "badge_codes": {"$addToSet": "$badge_code"},
                        "total_scans": {"$sum": 1},
                        "last_activity": {"$max": "$timestamp"},
                        "first_activity": {"$min": "$timestamp"}
                    }
                },
                {"$sort": {"last_activity": -1}}
            ]

            users = []
            for user in self.badge_repository.aggregate_users_from_badges(pipeline):
                users.append({
                    "username": user.get("username", ""),
                    "user_id": user.get("user_id", ""),
                    "first_name": user.get("first_name", ""),
                    "last_name": user.get("last_name", ""),
                    "badge_codes": user.get("badge_codes", []),
                    "total_scans": user.get("total_scans", 0),
                    "last_activity": DateHelper.to_iso(user.get("last_activity")),
                    "first_activity": DateHelper.to_iso(user.get("first_activity"))
                })

            return success_response({
                "users": users,
                "total_users": len(users)
            }, "Users retrieved successfully")

        except Exception as e:
            self.log_repository.error(f"Error retrieving users: {e}")
            return error_response(str(e), 500)

    def get_user(self, username):
        try:
            user = self.user_repository.find_by_username(username)
            if not user:
                return error_response("User not found", 404)

            return success_response({
                "user_id": str(user["_id"]),
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", ""),
                "company_name": user.get("company_name", ""),
                "user_role": user.get("role", "user"),
                "username": user.get("username", ""),
                "email": user.get("email", ""),
                "blocked": user.get("blocked", False)
            }, "User retrieved successfully")

        except Exception as e:
            self.log_repository.error(f"Error retrieving user {username}: {e}")
            return error_response(str(e), 500)

    def create_user(self, data):
        validation = UserValidator.validate_create_user(data)
        if validation:
            return validation

        try:
            username = data.get("username")
            email = data.get("email")
            password = data.get("password")

            if self.user_repository.find_by_username(username):
                return error_response("Username already exists", 400)

            if self.user_repository.find_by_email(email):
                return error_response("Email already exists", 400)

            hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

            self.user_repository.create_user({
                "username": username,
                "first_name": data.get("first_name", ""),
                "last_name": data.get("last_name", ""),
                "email": email,
                "company_name": data.get("company_name", ""),
                "password": hashed_pw.decode("utf-8"),
                "role": data.get("role", "user"),
                "blocked": data.get("blocked", False),
                "created_at": DateHelper.utc_now()
            })

            self.log_repository.info(f"User created: {username}")
            return success_response(None, "User created successfully", 201)

        except Exception as e:
            self.log_repository.error(f"Error creating user: {e}")
            return error_response("An error occurred while creating the user", 500)