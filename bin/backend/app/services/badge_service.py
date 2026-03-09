from bson.objectid import ObjectId
from app.validators.badge_validator import BadgeValidator
from app.utils.response import success_response, error_response
from app.utils.date_helper import DateHelper


class BadgeService:
    def __init__(self, badge_repository, log_repository):
        self.badge_repository = badge_repository
        self.log_repository = log_repository

    def _build_badge_query(self, source):
        query = {}
        filters_applied = {}

        start_date = source.get("start_date")
        end_date = source.get("end_date")
        month = source.get("month")
        day = source.get("day")
        badge_code = source.get("badge_code")
        user = source.get("user")

        if start_date or end_date:
            date_query = {}
            if start_date:
                date_query["$gte"] = DateHelper.parse_iso_date(start_date)
                filters_applied["start_date"] = start_date
            if end_date:
                date_query["$lte"] = DateHelper.parse_iso_date(end_date)
                filters_applied["end_date"] = end_date
            query["timestamp"] = date_query

        if month:
            month_int = int(month)
            if not 1 <= month_int <= 12:
                raise ValueError("Month must be between 1 and 12")
            query["$expr"] = {"$eq": [{"$month": "$timestamp"}, month_int]}
            filters_applied["month"] = month

        if day:
            day_int = int(day)
            if not 1 <= day_int <= 31:
                raise ValueError("Day must be between 1 and 31")
            if "$expr" in query:
                existing_expr = query["$expr"]
                query["$expr"] = {
                    "$and": [
                        existing_expr,
                        {"$eq": [{"$dayOfMonth": "$timestamp"}, day_int]}
                    ]
                }
            else:
                query["$expr"] = {"$eq": [{"$dayOfMonth": "$timestamp"}, day_int]}
            filters_applied["day"] = day

        if badge_code:
            query["badge_code"] = {"$regex": badge_code, "$options": "i"}
            filters_applied["badge_code"] = badge_code

        if user:
            query["$or"] = [
                {"username": {"$regex": user, "$options": "i"}},
                {"user_id": {"$regex": user, "$options": "i"}},
                {"first_name": {"$regex": user, "$options": "i"}},
                {"last_name": {"$regex": user, "$options": "i"}},
            ]
            filters_applied["user"] = user

        return query, filters_applied

    def get_badges(self, args):
        try:
            page, limit, validation_error = BadgeValidator.validate_pagination(
                args.get("page", 1),
                args.get("limit", 50)
            )
            if validation_error:
                return validation_error

            query, filters_applied = self._build_badge_query(args)

            total_count = self.badge_repository.count_badges(query)
            skip = (page - 1) * limit
            cursor = self.badge_repository.find_badges(query, skip, limit)

            badges = []
            for badge in cursor:
                badges.append({
                    "id": str(badge["_id"]),
                    "badge_code": badge.get("badge_code", ""),
                    "timestamp": DateHelper.to_iso(badge.get("timestamp")),
                    "username": badge.get("username", ""),
                    "user_id": badge.get("user_id", ""),
                    "first_name": badge.get("first_name", ""),
                    "last_name": badge.get("last_name", ""),
                    "action": badge.get("action", ""),
                    "location": badge.get("location", ""),
                    "device_id": badge.get("device_id", ""),
                    "raw_data": badge.get("raw_data", {}),
                    "processed": badge.get("processed", False)
                })

            total_pages = (total_count + limit - 1) // limit

            return success_response({
                "badges": badges,
                "pagination": {
                    "current_page": page,
                    "total_pages": total_pages,
                    "total_count": total_count,
                    "page_size": limit,
                    "has_next": page < total_pages,
                    "has_prev": page > 1
                },
                "filters_applied": filters_applied
            }, "Badges retrieved successfully")

        except ValueError as e:
            return error_response(str(e), 400)
        except Exception as e:
            self.log_repository.error(f"Error retrieving badge logs: {e}")
            return error_response(str(e), 500)

    def get_badge_by_id(self, badge_id):
        try:
            badge = self.badge_repository.find_badge_by_id(badge_id)
            if not badge:
                return error_response("Badge log not found", 404)

            return success_response({
                "id": str(badge["_id"]),
                "badge_code": badge.get("badge_code", ""),
                "timestamp": DateHelper.to_iso(badge.get("timestamp")),
                "username": badge.get("username", ""),
                "user_id": badge.get("user_id", ""),
                "first_name": badge.get("first_name", ""),
                "last_name": badge.get("last_name", ""),
                "action": badge.get("action", ""),
                "location": badge.get("location", ""),
                "device_id": badge.get("device_id", ""),
                "raw_data": badge.get("raw_data", {}),
                "processed": badge.get("processed", False),
                "created_at": DateHelper.to_iso(badge.get("created_at")),
                "updated_at": DateHelper.to_iso(badge.get("updated_at"))
            }, "Badge retrieved successfully")

        except Exception as e:
            self.log_repository.error(f"Error retrieving badge {badge_id}: {e}")
            return error_response("Invalid badge ID or internal error", 400)

    def create_badge_log(self, data):
        validation = BadgeValidator.validate_create_badge(data)
        if validation:
            return validation

        try:
            badge_log = {
                "badge_code": data.get("badge_code"),
                "timestamp": DateHelper.utc_now(),
                "username": data.get("username", ""),
                "user_id": data.get("user_id", ""),
                "first_name": data.get("first_name", ""),
                "last_name": data.get("last_name", ""),
                "action": data.get("action", "scan"),
                "location": data.get("location", ""),
                "device_id": data.get("device_id", ""),
                "raw_data": data.get("raw_data", {}),
                "processed": False,
                "created_at": DateHelper.utc_now(),
                "updated_at": DateHelper.utc_now()
            }

            result = self.badge_repository.insert_badge(badge_log)
            self.log_repository.info(f"Badge log created: {data.get('badge_code')}")

            return success_response({
                "id": str(result.inserted_id),
                "badge_code": badge_log["badge_code"],
                "timestamp": badge_log["timestamp"].isoformat()
            }, "Badge log created successfully", 201)

        except Exception as e:
            self.log_repository.error(f"Error creating badge log: {e}")
            return error_response(str(e), 500)

    def update_badge_log(self, badge_id, data):
        try:
            update_fields = {}
            updatable_fields = [
                "processed", "username", "user_id",
                "first_name", "last_name", "action", "location"
            ]

            for field in updatable_fields:
                if field in data:
                    update_fields[field] = data[field]

            if not update_fields:
                return error_response("No valid fields to update", 400)

            update_fields["updated_at"] = DateHelper.utc_now()

            result = self.badge_repository.update_badge(badge_id, update_fields)
            if result.matched_count == 0:
                return error_response("Badge log not found", 404)

            self.log_repository.info(f"Badge log updated: {badge_id}")
            return success_response(None, "Badge log updated successfully")

        except Exception as e:
            self.log_repository.error(f"Error updating badge log {badge_id}: {e}")
            return error_response("Invalid badge ID or internal error", 400)

    def delete_badge_log(self, badge_id):
        try:
            result = self.badge_repository.delete_badge(badge_id)
            if result.deleted_count == 0:
                return error_response("Badge log not found", 404)

            self.log_repository.info(f"Badge log deleted: {badge_id}")
            return success_response(None, "Badge log deleted successfully")

        except Exception as e:
            self.log_repository.error(f"Error deleting badge log {badge_id}: {e}")
            return error_response("Invalid badge ID or internal error", 400)

    def bulk_mark_processed(self, data):
        try:
            badge_ids = data.get("badge_ids", [])
            if not badge_ids:
                return error_response("badge_ids array is required", 400)

            object_ids = [ObjectId(bid) for bid in badge_ids]
            update_fields = {
                "processed": True,
                "updated_at": DateHelper.utc_now()
            }

            result = self.badge_repository.bulk_mark_processed(object_ids, update_fields)
            self.log_repository.info(f"Bulk marked {result.modified_count} badge logs")

            return success_response({
                "modified_count": result.modified_count
            }, f"Marked {result.modified_count} badge logs as processed")

        except Exception as e:
            self.log_repository.error(f"Error in bulk mark processed: {e}")
            return error_response("Invalid badge ID array or internal error", 400)