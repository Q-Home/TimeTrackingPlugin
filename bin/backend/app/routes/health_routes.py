from flask import Blueprint, jsonify
from app.utils.date_helper import DateHelper


def register_health_routes(mongo, api_prefix):
    health_bp = Blueprint("health", __name__)

    @health_bp.route(f"{api_prefix}/health", methods=["GET"])
    def health_check():
        """
        Health check endpoint
        ---
        tags:
          - Health
        produces:
          - application/json
        responses:
          200:
            description: API and database are healthy
          500:
            description: API or database is unhealthy
        """
        try:
            mongo.db.command("ping")
            return jsonify({
                "success": True,
                "status": "healthy",
                "database": mongo.db.name,
                "timestamp": DateHelper.utc_now().isoformat()
            }), 200
        except Exception as e:
            return jsonify({
                "success": False,
                "status": "unhealthy",
                "error": str(e),
                "timestamp": DateHelper.utc_now().isoformat()
            }), 500

    return health_bp