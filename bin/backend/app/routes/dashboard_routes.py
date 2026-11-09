from flask import Blueprint

from app.hr.routes import require, HR_ROLES


def register_dashboard_routes(dashboard_service, api_prefix):
    dashboard_bp = Blueprint("dashboard", __name__)

    @dashboard_bp.route(f"{api_prefix}/dashboard/summary", methods=["GET"])
    @require(*HR_ROLES)
    def get_dashboard_summary():
        return dashboard_service.get_admin_summary()

    return dashboard_bp
