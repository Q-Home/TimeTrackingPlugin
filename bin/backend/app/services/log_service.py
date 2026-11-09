import json
from pathlib import Path

from app.utils.date_helper import DateHelper
from app.utils.response import success_response, error_response


MQTT_DIAGNOSTICS_FILE = Path(__file__).resolve().parents[2] / "logs" / "mqtt_diagnostics.json"


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

    def get_mqtt_diagnostics(self):
        try:
            with MQTT_DIAGNOSTICS_FILE.open(encoding="utf-8") as source:
                snapshot = json.load(source)
        except FileNotFoundError:
            return success_response({"available": False})
        except (OSError, ValueError):
            return error_response("MQTT diagnostics could not be read", 503)

        if not isinstance(snapshot, dict) or not isinstance(snapshot.get("events"), list):
            return error_response("MQTT diagnostics could not be read", 503)

        return success_response({**snapshot, "available": True})
