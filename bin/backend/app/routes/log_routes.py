from flask import Blueprint, request
from app.decorators.permissions import internal_api_key_or_admin_required


def register_log_routes(log_service, api_prefix):
    log_bp = Blueprint("logs", __name__)

    @log_bp.route(f"{api_prefix}/logs/", methods=["GET"])
    @internal_api_key_or_admin_required
    def get_logs():
        limit = request.args.get("limit", default=500, type=int)
        limit = max(1, min(limit, 2000))
        return log_service.get_logs(limit=limit)

    return log_bp
