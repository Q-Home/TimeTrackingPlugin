from flasgger import Swagger


def init_swagger(app):
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": "apispec",
                "route": "/apispec.json",
                "rule_filter": lambda rule: True,
                "model_filter": lambda tag: True,
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs/",
    }

    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "TimeTracking API",
            "description": "API documentation for the TimeTracking system",
            "version": "1.0.0",
        },
        "basePath": "/",
        "schemes": ["http", "https"],
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Authorization header using the Bearer scheme. Example: Bearer <token>"
            }
        },
        "tags": [
            {"name": "Health", "description": "Health and status endpoints"},
            {"name": "Auth", "description": "Authentication endpoints"},
            {"name": "Users", "description": "User management endpoints"},
            {"name": "Badges", "description": "Badge log endpoints"},
        ],
        "definitions": {
            "SuccessResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": True},
                    "message": {"type": "string", "example": "Success"},
                    "data": {"type": "object"},
                },
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": False},
                    "error": {"type": "string", "example": "Bad request"},
                },
            },
            "LoginRequest": {
                "type": "object",
                "required": ["username", "password"],
                "properties": {
                    "username": {"type": "string", "example": "admin"},
                    "password": {"type": "string", "example": "ChangeThisAdminPassword123!"},
                },
            },
            "LoginResponseData": {
                "type": "object",
                "properties": {
                    "access_token": {"type": "string"},
                    "token_type": {"type": "string", "example": "Bearer"},
                    "username": {"type": "string", "example": "admin"},
                    "role": {"type": "string", "example": "admin"},
                },
            },
            "UserCreateRequest": {
                "type": "object",
                "required": ["username", "email", "password"],
                "properties": {
                    "username": {"type": "string", "example": "tibo"},
                    "first_name": {"type": "string", "example": "Tibo"},
                    "last_name": {"type": "string", "example": "Deneire"},
                    "email": {"type": "string", "example": "tibo@example.com"},
                    "company_name": {"type": "string", "example": "DSD Solutions"},
                    "password": {"type": "string", "example": "SecurePassword123"},
                    "role": {"type": "string", "example": "user"},
                    "blocked": {"type": "boolean", "example": False},
                },
            },
            "User": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "example": "65f01abc1234567890abcd12"},
                    "username": {"type": "string", "example": "tibo"},
                    "first_name": {"type": "string", "example": "Tibo"},
                    "last_name": {"type": "string", "example": "Deneire"},
                    "email": {"type": "string", "example": "tibo@example.com"},
                    "company_name": {"type": "string", "example": "DSD Solutions"},
                    "user_role": {"type": "string", "example": "user"},
                    "blocked": {"type": "boolean", "example": False},
                },
            },
            "BadgeCreateRequest": {
                "type": "object",
                "required": ["badge_code"],
                "properties": {
                    "badge_code": {"type": "string", "example": "BADGE001"},
                    "username": {"type": "string", "example": "tibo"},
                    "user_id": {"type": "string", "example": "EMP001"},
                    "first_name": {"type": "string", "example": "Tibo"},
                    "last_name": {"type": "string", "example": "Deneire"},
                    "action": {"type": "string", "example": "scan"},
                    "location": {"type": "string", "example": "front_door"},
                    "device_id": {"type": "string", "example": "esp32-reader-1"},
                    "raw_data": {"type": "object"},
                },
            },
            "BadgeUpdateRequest": {
                "type": "object",
                "properties": {
                    "processed": {"type": "boolean", "example": True},
                    "username": {"type": "string", "example": "tibo"},
                    "user_id": {"type": "string", "example": "EMP001"},
                    "first_name": {"type": "string", "example": "Tibo"},
                    "last_name": {"type": "string", "example": "Deneire"},
                    "action": {"type": "string", "example": "scan_in"},
                    "location": {"type": "string", "example": "office"},
                },
            },
            "Badge": {
                "type": "object",
                "properties": {
                    "id": {"type": "string", "example": "65f01abc1234567890abcd12"},
                    "badge_code": {"type": "string", "example": "BADGE001"},
                    "timestamp": {"type": "string", "example": "2026-03-09T12:00:00"},
                    "username": {"type": "string", "example": "tibo"},
                    "user_id": {"type": "string", "example": "EMP001"},
                    "first_name": {"type": "string", "example": "Tibo"},
                    "last_name": {"type": "string", "example": "Deneire"},
                    "action": {"type": "string", "example": "scan"},
                    "location": {"type": "string", "example": "front_door"},
                    "device_id": {"type": "string", "example": "esp32-reader-1"},
                    "raw_data": {"type": "object"},
                    "processed": {"type": "boolean", "example": False},
                    "created_at": {"type": "string", "example": "2026-03-09T12:00:00"},
                    "updated_at": {"type": "string", "example": "2026-03-09T12:00:00"},
                },
            },
            "BulkMarkProcessedRequest": {
                "type": "object",
                "required": ["badge_ids"],
                "properties": {
                    "badge_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "example": [
                            "65f01abc1234567890abcd12",
                            "65f01abc1234567890abcd13",
                        ],
                    }
                },
            },
        },
    }

    Swagger(app, config=swagger_config, template=swagger_template)