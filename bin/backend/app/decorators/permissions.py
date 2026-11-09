from functools import wraps

from flask_jwt_extended import verify_jwt_in_request, get_jwt
from app.utils.response import error_response
from app.constants.roles import Roles
from app.hr.routes import principal, TECH_ROLES
from app.decorators.internal_request import is_trusted_internal_request


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = principal()

        if claims.get("role") not in TECH_ROLES:
            return error_response("Admin access required", 403)

        return func(*args, **kwargs)
    return wrapper


def internal_api_key_or_admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if is_trusted_internal_request():
            return func(*args, **kwargs)

        verify_jwt_in_request()
        claims = principal()

        if claims.get("role") not in TECH_ROLES:
            return error_response("Admin access required", 403)

        return func(*args, **kwargs)

    return wrapper
