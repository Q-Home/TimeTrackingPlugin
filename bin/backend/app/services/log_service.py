from app.utils.date_helper import DateHelper
from app.utils.response import success_response, error_response


class LogService:
    def __init__(self, log_repository):
        self.log_repository = log_repository

    def get_logs(self, limit=500):
        try:
            logs = []
            for log_doc in self.log_repository.find_all(limit=limit):
                logs.append({
                    "id": str(log_doc.get("_id", "")),
                    "type": log_doc.get("type", "Info"),
                    "message": log_doc.get("message", ""),
                    "timestamp": DateHelper.to_iso(log_doc.get("timestamp")),
                })

            return success_response({
                "logs": logs,
                "total_logs": len(logs),
            }, "Logs retrieved successfully")
        except Exception as exc:
            return error_response(f"Failed to retrieve logs: {exc}", 500)
