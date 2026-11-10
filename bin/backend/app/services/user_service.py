import bcrypt
import re
from app.constants.roles import Roles
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

            badge_users = {}
            identity_group=dict(pipeline[0]['$group']);identity_group['_id']='$employee_id'
            employee_stats={str(item['_id']):item for item in self.badge_repository.aggregate_users_from_badges([
                {'$match':{'employee_id':{'$exists':True,'$ne':None}}},{'$group':identity_group}])}
            for badge_user in self.badge_repository.aggregate_users_from_badges(pipeline):
                username = badge_user.get("username", "")
                if not username:
                    continue
                badge_users[username] = badge_user

            users = []
            seen_usernames = set()

            registered_users=list(self.user_repository.find_all())
            from flask import current_app
            hr=current_app.extensions['hr_service'];identity_state=hr.state()
            known_ids={str(u['_id']) for u in registered_users}
            for db_user in registered_users:
                username = db_user.get("username", "")
                badge_user = employee_stats.get(str(db_user['_id'])) or badge_users.get(username, {})
                seen_usernames.add(username)

                users.append({
                    "username": username,
                    'employee_id':str(db_user['_id']),
                    'loxone_user_id':db_user.get('user_id',''),
                    'provisioned':db_user.get('provisioned_by')=='loxone',
                    'web_access':db_user.get('role','user') in Roles.WEB_LOGIN and not db_user.get('blocked'),
                    'account_exists':True,
                    "user_id": badge_user.get("user_id", str(db_user.get("_id", ""))),
                    "first_name": db_user.get("first_name", badge_user.get("first_name", "")),
                    "last_name": db_user.get("last_name", badge_user.get("last_name", "")),
                    "badge_code": db_user.get("badge_code", badge_user.get("badge_codes", [""])[0] if badge_user.get("badge_codes") else ""),
                    "badge_codes": [db_user.get("badge_code")] if db_user.get("badge_code") else badge_user.get("badge_codes", []),
                    "total_scans": badge_user.get("total_scans", 0),
                    "last_activity": DateHelper.to_iso(badge_user.get("last_activity")),
                    "first_activity": DateHelper.to_iso(badge_user.get("first_activity")),
                    "company_name": db_user.get("company_name", ""),
                    "email": db_user.get("email", ""),
                    'email_is_placeholder':bool(db_user.get('email_is_placeholder')),
                    "user_role": db_user.get("role", "user"),
                    "blocked": db_user.get("blocked", False),
                })

            for username, badge_user in badge_users.items():
                if username in seen_usernames:
                    continue
                if hr.resolve(badge_user,identity_state,registered_users) in known_ids:
                    continue

                users.append({
                    "username": username,
                    "user_id": badge_user.get("user_id", ""),
                    "first_name": badge_user.get("first_name", ""),
                    "last_name": badge_user.get("last_name", ""),
                    "badge_code": badge_user.get("badge_codes", [""])[0] if badge_user.get("badge_codes") else "",
                    "badge_codes": badge_user.get("badge_codes", []),
                    "total_scans": badge_user.get("total_scans", 0),
                    "last_activity": DateHelper.to_iso(badge_user.get("last_activity")),
                    "first_activity": DateHelper.to_iso(badge_user.get("first_activity")),
                    "company_name": "",
                    "email": "",
                    "user_role": "user",
                    "blocked": False,
                })

            users.sort(key=lambda user: (user.get("username") or "").lower())

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

            reserved_fields = {
                "_id",
                "username",
                "first_name",
                "last_name",
                "company_name",
                "role",
                "email",
                "badge_code",
                "blocked",
                "password",
                "created_at",
                "updated_at",
                "provisioning_key", "provisioned_by", "user_id", "loxone_username", "email_is_placeholder",
            }

            extra_fields = {
                key: value
                for key, value in user.items()
                if key not in reserved_fields
            }

            return success_response({
                "user_id": str(user["_id"]),
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", ""),
                "company_name": user.get("company_name", ""),
                "user_role": user.get("role", "user"),
                "username": user.get("username", ""),
                "email": user.get("email", ""),
                "badge_code": user.get("badge_code", ""),
                "blocked": user.get("blocked", False),
                "created_at": DateHelper.to_iso(user.get("created_at")),
                "updated_at": DateHelper.to_iso(user.get("updated_at")),
                "extra_fields": extra_fields,
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
            badge_code = (data.get("badge_code") or "").strip()

            if self.user_repository.find_by_username(username):
                return error_response("Username already exists", 400)

            from flask import current_app
            if 'username:'+username in current_app.extensions['hr_service'].state()['identity_links']:
                return error_response('Deze gebruikersnaam behoort bij een historische medewerker. Kies een nieuwe naam.',409)

            if self.user_repository.find_by_email(email):
                return error_response("Email already exists", 400)

            if badge_code and self.user_repository.find_by_badge_code(badge_code):
                return error_response("Badge code already exists", 400)

            hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

            self.user_repository.create_user({
                "username": username,
                "first_name": data.get("first_name", ""),
                "last_name": data.get("last_name", ""),
                "email": email,
                "company_name": data.get("company_name", ""),
                "badge_code": badge_code,
                "password": hashed_pw.decode("utf-8"),
                "role": data.get("role", "user"),
                "blocked": data.get("blocked", False),
                "created_at": DateHelper.utc_now(),
                "updated_at": DateHelper.utc_now()
            })

            self.log_repository.info(f"User created: {username}")
            return success_response(None, "User created successfully", 201)

        except Exception as e:
            self.log_repository.error(f"Error creating user: {e}")
            return error_response("An error occurred while creating the user", 500)

    def block_user(self, username):
        try:
            result = self.user_repository.update_by_username(username, {
                "blocked": True,
                "updated_at": DateHelper.utc_now()
            })

            if result.matched_count == 0:
                return error_response("User not found", 404)

            self.log_repository.info(f"User blocked: {username}")
            return success_response(None, "User blocked successfully", 200)

        except Exception as e:
            self.log_repository.error(f"Error blocking user {username}: {e}")
            return error_response("Failed to block user", 500)

    def unblock_user(self, username):
        try:
            result = self.user_repository.update_by_username(username, {
                "blocked": False,
                "updated_at": DateHelper.utc_now()
            })

            if result.matched_count == 0:
                return error_response("User not found", 404)

            self.log_repository.info(f"User unblocked: {username}")
            return success_response(None, "User unblocked successfully", 200)

        except Exception as e:
            self.log_repository.error(f"Error unblocking user {username}: {e}")
            return error_response("Failed to unblock user", 500)

    def delete_user(self, username):
        try:
            result = self.user_repository.update_by_username(username, {'blocked': True, 'archived': True})

            if result.matched_count == 0:
                return error_response("User not found", 404)

            self.log_repository.info(f"User deleted: {username}")
            return success_response(None, "User deleted successfully", 200)

        except Exception as e:
            self.log_repository.error(f"Error deleting user {username}: {e}")
            return error_response("Failed to delete user", 500)

    def update_user_by_id(self, user_id, data, allow_privileged_fields=True):
        try:
            existing_user = self.user_repository.find_by_id(user_id)
            if not existing_user:
                return error_response("User not found", 404)

            new_username = data.get("username", existing_user.get("username", "")).strip()
            new_email = data.get("email", existing_user.get("email", "")).strip()
            new_badge_code = (data.get("badge_code", existing_user.get("badge_code", "")) or "").strip()

            if not allow_privileged_fields:
                new_username = existing_user.get("username", "")
                new_badge_code = existing_user.get("badge_code", "")

            if len(new_username) < 3:
                return error_response("Username must be at least 3 characters", 400)

            if not new_email:
                return error_response("Email is required", 400)

            email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
            if not re.match(email_regex, new_email):
                return error_response("Invalid email address", 400)

            username_owner = self.user_repository.find_by_username(new_username)
            if username_owner and str(username_owner["_id"]) != user_id:
                return error_response("Username already exists", 400)

            email_owner = self.user_repository.find_by_email(new_email)
            if email_owner and str(email_owner["_id"]) != user_id:
                return error_response("Email already exists", 400)

            badge_owner = self.user_repository.find_by_badge_code(new_badge_code) if new_badge_code else None
            if badge_owner and str(badge_owner["_id"]) != user_id:
                return error_response("Badge code already exists", 400)

            role_value = data.get("user_role", data.get("role", existing_user.get("role", "user")))
            if not allow_privileged_fields:
                role_value = existing_user.get("role", "user")
            if role_value not in Roles.ALL:
                return error_response("Invalid role", 400)

            extra_fields = data.get("extra_fields", {})
            if extra_fields is None:
                extra_fields = {}
            if not allow_privileged_fields:
                extra_fields = {
                    key: existing_user.get(key)
                    for key in existing_user.keys()
                    if key not in {
                        "_id", "username", "first_name", "last_name", "company_name",
                        "role", "email", "badge_code", "blocked", "password", "created_at", "updated_at"
                    }
                }
            if not isinstance(extra_fields, dict):
                return error_response("Extra fields must be a JSON object", 400)

            reserved_fields = {
                "_id",
                "username",
                "first_name",
                "last_name",
                "company_name",
                "role",
                "email",
                "badge_code",
                "blocked",
                "password",
                "created_at",
                "updated_at",
                "provisioning_key", "provisioned_by", "user_id", "loxone_username", "email_is_placeholder",
            }

            sanitized_extra_fields = {
                key: value
                for key, value in extra_fields.items()
                if key not in reserved_fields
            }

            existing_extra_keys = {
                key for key in existing_user.keys()
                if key not in reserved_fields
            }

            unset_fields = {
                key: ""
                for key in existing_extra_keys
                if key not in sanitized_extra_fields
            }

            update_fields = {
                "username": new_username,
                "first_name": data.get("first_name", existing_user.get("first_name", "")),
                "last_name": data.get("last_name", existing_user.get("last_name", "")),
                "company_name": data.get("company_name", existing_user.get("company_name", "")),
                "email": new_email,
                "badge_code": new_badge_code,
                "role": role_value,
                "blocked": data.get("blocked", existing_user.get("blocked", False)) if allow_privileged_fields else existing_user.get("blocked", False),
                "updated_at": DateHelper.utc_now()
            }

            update_fields.update(sanitized_extra_fields)
            if existing_user.get('email_is_placeholder') and new_email!=existing_user.get('email'):
                update_fields['email_is_placeholder']=False

            from flask import current_app
            current_app.extensions['hr_service'].remember_username(existing_user['username'], new_username, user_id)
            result = self.user_repository.update_by_id(user_id, update_fields, unset_fields)

            if result.matched_count == 0:
                return error_response("User not found", 404)

            self.log_repository.info(f"User updated by id: {user_id}")
            return success_response(None, "User updated successfully", 200)

        except Exception as e:
            self.log_repository.error(f"Error updating user {user_id}: {e}")
            return error_response("Failed to update user", 500)

    def update_password_by_id(self, user_id, data, require_current=False):
        try:
            if not isinstance(data,dict):return error_response('Verstuur geldige wachtwoordvelden.',400)
            existing_user = self.user_repository.find_by_id(user_id)
            if not existing_user:
                return error_response("User not found", 404)

            password = data.get("password", "")
            if not isinstance(password,str):
                return error_response('Geef een geldig nieuw wachtwoord.',400)
            if len(password) < 6 or not password.strip():
                return error_response('Het nieuwe wachtwoord moet minstens 6 tekens bevatten.',400)
            if len(password.encode('utf-8'))>72:
                return error_response('Het nieuwe wachtwoord is te lang (maximaal 72 UTF-8 bytes).',400)
            if require_current:
                current=data.get('current_password')
                if not isinstance(current,str) or not current:
                    return error_response('Vul je huidige wachtwoord in.',400)
                try:valid=bcrypt.checkpw(current.encode('utf-8'),existing_user['password'].encode('utf-8'))
                except (ValueError,KeyError,TypeError):valid=False
                if not valid:return error_response('Je huidige wachtwoord is niet juist.',400)

            hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

            result = self.user_repository.update_password_if_unchanged(user_id, existing_user.get('password'), {
                "password": hashed_pw.decode("utf-8"),
                "updated_at": DateHelper.utc_now()
            })

            if result.matched_count == 0:
                return error_response('Het account is ondertussen gewijzigd. Vernieuw en probeer opnieuw.',409)

            self.log_repository.info(f"Password updated for user id: {user_id}")
            return success_response(None, "Password updated successfully", 200)

        except Exception as e:
            self.log_repository.error(f"Error updating password for user {user_id}: {e}")
            return error_response("Failed to update password", 500)
