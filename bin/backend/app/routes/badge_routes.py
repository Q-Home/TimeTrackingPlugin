from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from app.decorators.permissions import admin_required


def register_badge_routes(badge_service, api_prefix):
    badge_bp = Blueprint("badges", __name__)

    @badge_bp.route(f"{api_prefix}/badges/", methods=["GET"])
    @jwt_required()
    def get_badges():
        """
        Get badge logs
        ---
        tags:
          - Badges
        security:
          - Bearer: []
        produces:
          - application/json
        parameters:
          - in: query
            name: page
            type: integer
            required: false
            example: 1
          - in: query
            name: limit
            type: integer
            required: false
            example: 50
          - in: query
            name: start_date
            type: string
            required: false
            example: 2026-03-01T00:00:00Z
          - in: query
            name: end_date
            type: string
            required: false
            example: 2026-03-09T23:59:59Z
          - in: query
            name: month
            type: integer
            required: false
            example: 3
          - in: query
            name: day
            type: integer
            required: false
            example: 9
          - in: query
            name: badge_code
            type: string
            required: false
            example: ABC123
          - in: query
            name: user
            type: string
            required: false
            example: tibo
        responses:
          200:
            description: Badge logs retrieved successfully
            schema:
              allOf:
                - $ref: '#/definitions/SuccessResponse'
                - type: object
                  properties:
                    data:
                      type: object
          400:
            description: Invalid filter values
            schema:
              $ref: '#/definitions/ErrorResponse'
          401:
            description: Authentication required
            schema:
              $ref: '#/definitions/ErrorResponse'
        """
        return badge_service.get_badges(request.args)

    @badge_bp.route(f"{api_prefix}/badges/<badge_id>", methods=["GET"])
    @jwt_required()
    def get_badge_by_id(badge_id):
        """
        Get badge log by ID
        ---
        tags:
          - Badges
        security:
          - Bearer: []
        produces:
          - application/json
        parameters:
          - in: path
            name: badge_id
            type: string
            required: true
            example: 65f01abc1234567890abcd12
        responses:
          200:
            description: Badge retrieved successfully
            schema:
              allOf:
                - $ref: '#/definitions/SuccessResponse'
                - type: object
                  properties:
                    data:
                      $ref: '#/definitions/Badge'
          404:
            description: Badge log not found
            schema:
              $ref: '#/definitions/ErrorResponse'
        """
        return badge_service.get_badge_by_id(badge_id)

    @badge_bp.route(f"{api_prefix}/badges/", methods=["POST"])
    @jwt_required()
    def create_badge():
        """
        Create a badge log
        ---
        tags:
          - Badges
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
              $ref: '#/definitions/BadgeCreateRequest'
        responses:
          201:
            description: Badge log created successfully
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
        """
        return badge_service.create_badge_log(request.get_json() or {})

    @badge_bp.route(f"{api_prefix}/badges/<badge_id>", methods=["PUT"])
    @jwt_required()
    def update_badge(badge_id):
        """
        Update a badge log
        ---
        tags:
          - Badges
        security:
          - Bearer: []
        consumes:
          - application/json
        produces:
          - application/json
        parameters:
          - in: path
            name: badge_id
            type: string
            required: true
          - in: body
            name: body
            required: true
            schema:
              $ref: '#/definitions/BadgeUpdateRequest'
        responses:
          200:
            description: Badge updated successfully
            schema:
              $ref: '#/definitions/SuccessResponse'
          400:
            description: Invalid update or badge ID
            schema:
              $ref: '#/definitions/ErrorResponse'
          404:
            description: Badge log not found
            schema:
              $ref: '#/definitions/ErrorResponse'
        """
        return badge_service.update_badge_log(badge_id, request.get_json() or {})

    @badge_bp.route(f"{api_prefix}/badges/<badge_id>", methods=["DELETE"])
    @admin_required
    def delete_badge(badge_id):
        """
        Delete a badge log
        ---
        tags:
          - Badges
        security:
          - Bearer: []
        produces:
          - application/json
        parameters:
          - in: path
            name: badge_id
            type: string
            required: true
        responses:
          200:
            description: Badge deleted successfully
            schema:
              $ref: '#/definitions/SuccessResponse'
          403:
            description: Admin required
            schema:
              $ref: '#/definitions/ErrorResponse'
          404:
            description: Badge log not found
            schema:
              $ref: '#/definitions/ErrorResponse'
        """
        return badge_service.delete_badge_log(badge_id)

    @badge_bp.route(f"{api_prefix}/badges/bulk/mark-processed", methods=["POST"])
    @admin_required
    def bulk_mark_processed():
        """
        Mark multiple badge logs as processed
        ---
        tags:
          - Badges
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
              $ref: '#/definitions/BulkMarkProcessedRequest'
        responses:
          200:
            description: Badge logs marked as processed
            schema:
              $ref: '#/definitions/SuccessResponse'
          400:
            description: Invalid badge IDs
            schema:
              $ref: '#/definitions/ErrorResponse'
          403:
            description: Admin required
            schema:
              $ref: '#/definitions/ErrorResponse'
        """
        return badge_service.bulk_mark_processed(request.get_json() or {})

    return badge_bp