from functools import wraps

from flask_jwt_extended import verify_jwt_in_request
from app.decorators.internal_request import is_trusted_internal_request


def internal_api_key_or_jwt_required():
    """Allow either a normal JWT bearer token or a shared internal API key."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if is_trusted_internal_request():
                return fn(*args, **kwargs)

            verify_jwt_in_request()
            return fn(*args, **kwargs)

        return wrapper

    return decorator
