from flask import Blueprint, request


def register_auth_routes(auth_service, api_prefix):
    auth_bp = Blueprint("auth", __name__)

    @auth_bp.route(f"{api_prefix}/login", methods=["POST"])
    def login():
        """
        Login user
        ---
        tags:
          - Auth
        consumes:
          - application/json
        produces:
          - application/json
        parameters:
          - in: body
            name: body
            required: true
            schema:
              $ref: '#/definitions/LoginRequest'
        responses:
          200:
            description: Login successful
            schema:
              allOf:
                - $ref: '#/definitions/SuccessResponse'
                - type: object
                  properties:
                    data:
                      $ref: '#/definitions/LoginResponseData'
          401:
            description: Invalid credentials
            schema:
              $ref: '#/definitions/ErrorResponse'
          403:
            description: Account blocked
            schema:
              $ref: '#/definitions/ErrorResponse'
        """
        return auth_service.login(request.get_json() or {})

    return auth_bp