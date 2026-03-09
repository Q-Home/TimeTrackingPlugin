from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from datetime import datetime
from app.utils.response import error_response


def register_timesheet_routes(timesheet_service, api_prefix):
    timesheet_bp = Blueprint("timesheets", __name__)

    @timesheet_bp.route(f"{api_prefix}/timesheets/<username>", methods=["GET"])
    @jwt_required()
    def get_timesheet_for_day(username):
        date_str = request.args.get("date")

        if not date_str:
            return error_response("date query parameter is required, format YYYY-MM-DD", 400)

        try:
            day = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return error_response("Invalid date format. Use YYYY-MM-DD", 400)

        result = timesheet_service.get_user_timesheet_for_day(username, day)
        return {
            "success": True,
            "message": "Timesheet calculated successfully",
            "data": result
        }, 200

    return timesheet_bp