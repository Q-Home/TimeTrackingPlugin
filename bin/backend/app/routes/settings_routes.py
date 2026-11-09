from flask import Blueprint, request

from app.decorators.permissions import admin_required


def register_settings_routes(settings_service, api_prefix):
    settings_bp = Blueprint("settings", __name__)

    @settings_bp.route(f"{api_prefix}/settings/branding", methods=["GET"])
    def get_branding():
        return settings_service.get_branding()

    @settings_bp.route(f"{api_prefix}/settings/branding", methods=["PUT"])
    @admin_required
    def update_branding():
        return settings_service.update_branding(request.get_json() or {})

    return settings_bp
