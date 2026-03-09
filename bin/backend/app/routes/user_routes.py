from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.decorators.permissions import admin_required


def register_user_routes(user_service, api_prefix):
    user_bp = Blueprint("users", __name__)

    @user_bp.route(f"{api_prefix}/users/", methods=["GET"])
    @jwt_required()
    def get_users():
        """
        Get all users derived from badge logs
        ---
        tags:
          - Users
        security:
          - Bearer: []
        produces:
          - application/json
        responses:
          200:
            description: Users retrieved successfully
            schema:
              allOf:
                - $ref: '#/definitions/SuccessResponse'
                - type: object
                  properties:
                    data:
                      type: object
                      properties:
                        users:
                          type: array
                          items:
                            type: object
                        total_users:
                          type: integer
                          example: 10
          401:
            description: Authentication required
            schema:
              $ref: '#/definitions/ErrorResponse'
        """
        return user_service.get_users()

    @user_bp.route(f"{api_prefix}/users/<username>", methods=["GET"])
    @jwt_required()
    def get_user(username):
        """
        Get one user by username
        ---
        tags:
          - Users
        security:
          - Bearer: []
        produces:
          - application/json
        parameters:
          - in: path
            name: username
            type: string
            required: true
            example: admin
        responses:
          200:
            description: User retrieved successfully
            schema:
              allOf:
                - $ref: '#/definitions/SuccessResponse'
                - type: object
                  properties:
                    data:
                      $ref: '#/definitions/User'
          404:
            description: User not found
            schema:
              $ref: '#/definitions/ErrorResponse'
        """
        return user_service.get_user(username)

    @user_bp.route(f"{api_prefix}/users/", methods=["POST"])
    @admin_required
    def create_user():
        """
        Create a new user
        ---
        tags:
          - Users
        security:
          - Bearer: []
        consumes:
          - application/json
        produces:
          - application/json
        parameters:
          - in: body
            name: body
            required: true
            schema:
              $ref: '#/definitions/UserCreateRequest'
        responses:
          201:
            description: User created successfully
            schema:
              $ref: '#/definitions/SuccessResponse'
          400:
            description: Validation error
            schema:
              $ref: '#/definitions/ErrorResponse'
          401:
            description: Authentication required
            schema:
              $ref: '#/definitions/ErrorResponse'
          403:
            description: Admin required
            schema:
              $ref: '#/definitions/ErrorResponse'
        """
        return user_service.create_user(request.get_json() or {})

    @user_bp.route(f"{api_prefix}/users/<username>/block", methods=["PUT"])
    @admin_required
    def block_user(username):
        return user_service.block_user(username)

    @user_bp.route(f"{api_prefix}/users/<username>/unblock", methods=["PUT"])
    @admin_required
    def unblock_user(username):
        return user_service.unblock_user(username)

    @user_bp.route(f"{api_prefix}/users/<username>", methods=["DELETE"])
    @admin_required
    def delete_user(username):
        return user_service.delete_user(username)

    @user_bp.route(f"{api_prefix}/users/<user_id>", methods=["PUT"])
    @admin_required
    def update_user_by_id(user_id):
        return user_service.update_user_by_id(user_id, request.get_json() or {})

    @user_bp.route(f"{api_prefix}/users/<user_id>/password", methods=["PUT"])
    @admin_required
    def update_password_by_id(user_id):
        return user_service.update_password_by_id(user_id, request.get_json() or {})

    return user_bp