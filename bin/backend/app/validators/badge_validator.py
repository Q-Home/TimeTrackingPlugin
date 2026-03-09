from app.utils.response import error_response
from app.constants.actions import BadgeActions


class BadgeValidator:
    @staticmethod
    def validate_create_badge(data):
        badge_code = data.get("badge_code")
        action = data.get("action", BadgeActions.SCAN)

        if not badge_code:
            return error_response("badge_code is required", 400)

        if action not in BadgeActions.ALL:
            return error_response("Invalid badge action", 400)

        return None

    @staticmethod
    def validate_pagination(page, limit):
        try:
            page = int(page)
            limit = int(limit)
        except ValueError:
            return None, None, error_response("page and limit must be integers", 400)

        if page < 1:
            return None, None, error_response("page must be >= 1", 400)

        if limit < 1 or limit > 100:
            return None, None, error_response("limit must be between 1 and 100", 400)

        return page, limit, None