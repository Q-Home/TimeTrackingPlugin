from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from datetime import datetime
from app.constants.roles import Roles
from app.utils.response import error_response


def register_timesheet_routes(timesheet_service, api_prefix):
    timesheet_bp = Blueprint("timesheets", __name__)

    def resolve_allowed_username(requested_username):
        claims = get_jwt()
        current_username = get_jwt_identity()
        role = claims.get("role", Roles.USER)

        if role == Roles.ADMIN:
            return requested_username

        if requested_username != current_username:
            return None

        return current_username

    @timesheet_bp.route(f"{api_prefix}/timesheets/<username>", methods=["GET"])
    @jwt_required()
    def get_timesheet_for_day(username):
        allowed_username = resolve_allowed_username(username)
        if not allowed_username:
            return error_response("You can only view your own timesheet", 403)

        date_str = request.args.get("date")

        if not date_str:
            return error_response("date query parameter is required, format YYYY-MM-DD", 400)

        try:
            day = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return error_response("Invalid date format. Use YYYY-MM-DD", 400)

        result = timesheet_service.get_user_timesheet_for_day(allowed_username, day)

        return jsonify({
            "success": True,
            "message": "Timesheet calculated successfully",
            "data": result
        }), 200

    @timesheet_bp.route(f"{api_prefix}/timesheets/<username>/range", methods=["GET"])
    @jwt_required()
    def get_timesheet_for_range(username):
        allowed_username = resolve_allowed_username(username)
        if not allowed_username:
            return error_response("You can only view your own timesheet", 403)

        start_str = request.args.get("start")
        end_str = request.args.get("end")

        if not start_str or not end_str:
            return error_response("start and end query parameters are required, format YYYY-MM-DD", 400)

        try:
            start_date = datetime.strptime(start_str, "%Y-%m-%d")
            end_date = datetime.strptime(end_str, "%Y-%m-%d")
        except ValueError:
            return error_response("Invalid date format. Use YYYY-MM-DD", 400)

        if end_date < start_date:
            return error_response("end date must be greater than or equal to start date", 400)

        end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

        result = timesheet_service.get_user_timesheet_for_range(allowed_username, start_date, end_date)

        return jsonify({
            "success": True,
            "message": "Timesheet range calculated successfully",
            "data": result
        }), 200

    return timesheet_bp
