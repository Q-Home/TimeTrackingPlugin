from flask import Blueprint

from app.decorators.permissions import admin_required


def register_dashboard_routes(dashboard_service, api_prefix):
    dashboard_bp = Blueprint("dashboard", __name__)

    @dashboard_bp.route(f"{api_prefix}/dashboard/summary", methods=["GET"])
    @admin_required
    def get_dashboard_summary():
        return dashboard_service.get_admin_summary()

    return dashboard_bp
