# ---------------- Imports ----------------
import os
import time
import json
import traceback
from datetime import datetime, timezone
import requests
import paho.mqtt.client as mqtt
from zoneinfo import ZoneInfo  # ✅ ingebouwde tijdzone-ondersteuning sinds Python 3.9

# ---------------- Configuration ----------------
DB_FOLDER = "/opt/loxberry/log/plugins/timetrackingplugin"
DB_NAME = os.getenv("MONGO_DB_NAME", "timetracking")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "entrees")
LOGFILE = os.path.join(DB_FOLDER, "timetracking_mqtt.log")

# MongoDB connection - configureerbaar via environment variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/timetracking")
MONGO_HOST = os.getenv("MONGO_HOST", "localhost")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))

# MQTT settings - configureerbaar
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "miniserver/timetracking")
MQTT_STATS_TOPIC = os.getenv("MQTT_STATS_TOPIC", "miniserver/timetracking/getstats")
MQTT_PUB_TOPIC = os.getenv("MQTT_PUB_TOPIC", "loxberry/timetracking")
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

# Backend API endpoint
BACKEND_API = os.getenv("BACKEND_API", "http://localhost:5000/api/v1")
INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY", "")
MQTT_LOG_PAYLOADS = os.getenv("MQTT_LOG_PAYLOADS", "true").lower() == "true"

# Belgische tijdzone
BELGIUM_TZ = ZoneInfo("Europe/Brussels")


def backend_headers():
    headers = {}
    if INTERNAL_API_KEY:
        headers["X-Internal-API-Key"] = INTERNAL_API_KEY
    return headers


def parse_to_belgium(incoming_ts):
    """Parse various timestamp formats and return a timezone-aware datetime in Europe/Brussels.

    - Accepts ISO8601 strings with offsets (e.g. +00:00), strings ending with Z, naive timestamps.
    - If the timestamp is naive (no tzinfo) we assume UTC (same behaviour as before).
    - Returns a datetime in BELGIUM_TZ or None if parsing failed.
    """
    if not incoming_ts:
        return None

    # If it's already a datetime, convert directly
    if isinstance(incoming_ts, datetime):
        dt = incoming_ts
    else:
        s = str(incoming_ts).strip()
        # Normalize 'Z' to +00:00 which datetime.fromisoformat understands
        if s.endswith('Z'):
            s = s[:-1] + '+00:00'

        # Try the convenient ISO parser first
        try:
            dt = datetime.fromisoformat(s)
        except Exception:
            # Fallback: try a couple of common patterns
            try:
                # e.g. 2025-10-15T06:48:11+0000 (no colon in offset)
                if len(s) >= 5 and (s[-5] in ['+', '-'] and s[-3] != ':'):
                    # insert colon before last two digits
                    s = s[:-2] + ':' + s[-2:]
                dt = datetime.fromisoformat(s)
            except Exception:
                try:
                    # Last resort: parse without offset and assume naive local format, treat as UTC
                    # Common format: YYYY-MM-DDTHH:MM:SS(.ffffff)
                    dt = datetime.fromisoformat(s)
                except Exception:
                    return None

    # If still naive (no tzinfo), assume UTC (preserve previous behaviour)
    if dt.tzinfo is None:
        from datetime import timezone

        dt = dt.replace(tzinfo=timezone.utc)

    # Convert to Belgium timezone (ZoneInfo handles DST automatically)
    try:
        return dt.astimezone(BELGIUM_TZ)
    except Exception:
        return None

# ---------------- Logging Function ----------------
def log(msg):
    now = datetime.now(BELGIUM_TZ).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[PRINT][{now}] {msg}")
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    with open(LOGFILE, "a") as f:
        f.write(f"[{now}] {msg}\n")


def log_exception(context, exc):
    details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    log(f"{context}: {exc}")
    log(details.rstrip())

# ---------------- API Client ----------------
def insert_to_db(badge_data):
    """
    Verstuurt badge_data naar de backend API.
    Corrigeert automatisch first_name/last_name op basis van username als ze leeg zijn.
    """
    print(f"[PRINT] insert_to_db called with data={badge_data}")

    # Normalize badge_code: send JSON null when empty or missing
    badge_code = badge_data.get("badge_code")
    if badge_code is None or (isinstance(badge_code, str) and badge_code.strip() == ""):
        badge_data["badge_code"] = None
        log("badge_code empty or missing -> sending JSON null")
        print("[PRINT] badge_code empty or missing -> sending JSON null")
    else:
        badge_data["badge_code"] = badge_code.strip()

    # Ensure action has a default
    action = badge_data.get("action")
    if action is None or (isinstance(action, str) and action.strip() == ""):
        badge_data["action"] = "scan"
    else:
        badge_data["action"] = action.strip()

    # --- Automatisch splitsen van username op punt ---
    username = badge_data.get("username", "")
    first_name = badge_data.get("first_name", "").strip()
    last_name = badge_data.get("last_name", "").strip()

    if "." in username and (not first_name and not last_name):
        parts = username.split(".", 1)
        # Preserve the original casing/spacing provided in the username parts
        badge_data["first_name"] = parts[0].strip()
        badge_data["last_name"] = parts[1].strip()
        log(f"Auto-split username '{username}' -> first_name='{parts[0].strip()}', last_name='{parts[1].strip()}'")
        print(f"[PRINT] Auto-split username '{username}' -> first_name='{parts[0].strip()}', last_name='{parts[1].strip()}'")

    try:
        # Log API request
        log(f"Sending API request to {BACKEND_API}/badges/")
        print(f"[PRINT] API request payload: {badge_data}")

        # Zorg dat we een geldige timestamp hebben en converteer naar Belgische tijd
        # Accept both 'scan_time' and 'timestamp' from upstream; prefer 'scan_time' when present
        incoming_ts = badge_data.get('scan_time') or badge_data.get('timestamp')
        if incoming_ts:
            parsed_belgium = parse_to_belgium(incoming_ts)
            if parsed_belgium is not None:
                badge_data['timestamp'] = parsed_belgium.isoformat()
                badge_data['scan_time'] = parsed_belgium.isoformat()
                log(f"Parsed incoming timestamp '{incoming_ts}' -> Belgium time '{badge_data['timestamp']}'")
            else:
                # Failed to parse inbound timestamp; fallback to now in Belgium TZ
                now_iso = datetime.now(BELGIUM_TZ).isoformat()
                badge_data['timestamp'] = now_iso
                badge_data['scan_time'] = now_iso
                log(f"Failed to parse incoming timestamp '{incoming_ts}' - defaulting to now Belgium time {now_iso}")
        else:
            # No incoming timestamp provided - set to now Belgium time
            now_iso = datetime.now(BELGIUM_TZ).isoformat()
            badge_data['timestamp'] = now_iso
            badge_data['scan_time'] = now_iso

        # Always include the server-received timestamp (Belgium time) for auditing
        received_iso = datetime.now(BELGIUM_TZ).isoformat()
        badge_data['received_at'] = received_iso
        log(f"Server received_at set to Belgium time {received_iso}")

        # Maak de API-aanroep
        response = requests.post(
            f"{BACKEND_API}/badges/",
            json=badge_data,
            headers=backend_headers(),
            timeout=10,
        )
        response.raise_for_status()

        log(f"Successfully sent badge data to API: {response.status_code}")
        print(f"[PRINT] API response: {response.status_code} {response.text}")
        return True

    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed: {e}"
        print(f"[PRINT][ERROR] {error_msg}")
        log(error_msg)
        return False

def get_user_logs(username):
    print(f"[PRINT] get_user_logs called for user: {username}")
    logs = []
    try:
        log(f"Fetching logs for user: {username}")
        response = requests.get(
            f"{BACKEND_API}/badges/search",
            json={"username": username},
            headers=backend_headers(),
            timeout=10,
        )
        response.raise_for_status()
        logs = response.json()
        print(f"[PRINT] Found {len(logs)} logs for {username}")
        log(f"Found {len(logs)} logs for {username}")
    except requests.exceptions.RequestException as e:
        error_msg = f"API request failed: {e}"
        print(f"[PRINT][ERROR] {error_msg}")
        log(error_msg)
    return logs
def publish_to_loxone(client, badgecode, user, scan_time, status):
    """Publish a simplified Loxone-compatible string to `MQTT_PUB_TOPIC`."""
    try:
        if badgecode is None or (isinstance(badgecode, str) and badgecode.strip() == ""):
            # No badgecode available -> publish time and status only
            message = f"{scan_time},{status}"
        else:
            message = f"{badgecode},{user},{scan_time},{status}"

        log(f"Publishing to Loxone MQTT: {message}")
        print(f"[PRINT] Publishing to MQTT topic {MQTT_PUB_TOPIC}: {message}")
        client.publish(MQTT_PUB_TOPIC, message)
    except Exception as e:
        print(f"[PRINT][ERROR] Failed to publish to Loxone MQTT: {e}")
        log(f"Failed to publish to Loxone MQTT: {e}")


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[PRINT] on_connect called with rc={rc}")
    if rc == 0:
        log("Connected to MQTT broker successfully.")
        print(f"[PRINT] Subscribing to {MQTT_TOPIC} and {MQTT_STATS_TOPIC}")
        client.subscribe(MQTT_TOPIC)
        client.subscribe(MQTT_STATS_TOPIC)
        log(f"Subscribed to topics: {MQTT_TOPIC} and {MQTT_STATS_TOPIC}")
    else:
        log(f"Failed to connect to MQTT broker, return code {rc}")
        print(f"[PRINT][ERROR] Failed to connect to MQTT broker, rc={rc}")


def on_disconnect(client, userdata, disconnect_flags, rc, properties=None):
    log(f"Disconnected from MQTT broker. rc={rc}")
    print(f"[PRINT][WARNING] MQTT disconnected rc={rc}")


def on_subscribe(client, userdata, mid, reason_code_list, properties=None):
    log(f"MQTT subscribe acknowledged. mid={mid}, reason_codes={reason_code_list}")
    print(f"[PRINT] MQTT subscribe acknowledged. mid={mid}, reason_codes={reason_code_list}")

def on_message(client, userdata, msg):
    print(f"[PRINT] on_message called. Topic: {msg.topic}, Payload length: {len(msg.payload)}")
    payload = msg.payload.decode().strip()
    topic = msg.topic
    if MQTT_LOG_PAYLOADS:
        log(f"Received MQTT message on topic '{topic}': {payload}")
    else:
        log(f"Received MQTT message on topic '{topic}' (payload logging disabled, {len(msg.payload)} bytes)")

    if topic == MQTT_TOPIC:
        # Accept either a JSON object payload or the legacy semicolon-separated string
        try:
            badge_data = None
            try:
                parsed = json.loads(payload)
                if isinstance(parsed, dict):
                    badge_data = parsed
                    print(f"[PRINT] Parsed MQTT JSON data: {badge_data}")
            except json.JSONDecodeError:
                # Not JSON - try legacy format below
                pass

            if badge_data is None:
                # Legacy expected format: badgecode;username;scan_time;action
                parts = payload.split(";")
                print(f"[PRINT] Payload parts (legacy): {parts}")
                if len(parts) >= 4:
                    badge_data = {
                        "badge_code": parts[0].strip() or None,
                        "username": parts[1].strip(),
                        "scan_time": parts[2].strip(),
                        "action": parts[3].strip()
                    }
                elif payload == "Access Denied":
                    badge_data = {
                        "badge_code": None,
                        "username": "",
                        "scan_time": datetime.now(BELGIUM_TZ).isoformat(),
                        "action": "none",
                        "status": "Access Denied"
                    }
                else:
                    print(f"[PRINT][ERROR] Ignored malformed message: {payload}")
                    log(f"Ignored malformed message: {payload}")
                    badge_data = None

            if badge_data:
                # Ensure status field
                if "status" not in badge_data:
                    badge_data["status"] = "Access Granted"

                # Ensure scan_time is present
                if "scan_time" not in badge_data or not badge_data.get("scan_time"):
                    badge_data["scan_time"] = datetime.now(BELGIUM_TZ).isoformat()

                # Call API
                success = insert_to_db(badge_data)
                log(f"insert_to_db result={success} for user='{badge_data.get('username', '')}' action='{badge_data.get('action', '')}'")

                # Publish to Loxone-friendly topic
                publish_to_loxone(client,
                                  badge_data.get("badge_code"),
                                  badge_data.get("username", ""),
                                  badge_data.get("scan_time"),
                                  badge_data.get("status", "Access Granted"))

        except Exception as e:
            print(f"[PRINT][ERROR] Failed to process badge data: {e}")
            log_exception("Failed to process badge data", e)

    elif topic == MQTT_STATS_TOPIC:
        try:
            username = payload.strip()
            print(f"[PRINT] Stats requested for user '{username}'")
            log(f"Stats requested for user '{username}'")
            logs = get_user_logs(username)
            if logs:
                print(f"[PRINT] Found {len(logs)} logs for user '{username}'")
                log(f"Found {len(logs)} logs for user '{username}'")
            else:
                print(f"[PRINT] No logs found for user '{username}'")
                log(f"No logs found for user '{username}'")
        except Exception as e:
            print(f"[PRINT][ERROR] Error handling stats request: {e}")
            log_exception("Error handling stats request", e)

# ---------------- Main Loop ----------------
def main():
    print("[PRINT] main() started")
    log("Starting timetracking MQTT script...")
    log(f"MongoDB URI: {MONGO_URI}")
    log(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")
    log(f"MQTT Topic: {MQTT_TOPIC}")
    log(f"MQTT Stats Topic: {MQTT_STATS_TOPIC}")
    log(f"MQTT Publish Topic: {MQTT_PUB_TOPIC}")
    log(f"Backend API: {BACKEND_API}")
    log(f"Internal API key configured: {'yes' if INTERNAL_API_KEY else 'no'}")
    log(f"Using timezone: Europe/Brussels")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
    client.on_subscribe = on_subscribe

    try:
        log(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
        print(f"[PRINT] Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except Exception as e:
        print(f"[PRINT][ERROR] MQTT connection error: {e}")
        log(f"MQTT connection error: {e}")
        return

    client.loop_start()
    print("[PRINT] MQTT loop started.")
    log("MQTT loop started.")

    try:
        while True:
            print("[PRINT] Main loop heartbeat - " + datetime.now(BELGIUM_TZ).isoformat())
            time.sleep(1)
    except KeyboardInterrupt:
        print("[PRINT] KeyboardInterrupt: Shutting down gracefully.")
        log("KeyboardInterrupt: Shutting down gracefully.")
    except Exception as e:
        print(f"[PRINT][ERROR] Unexpected error in main loop: {e}")
        log_exception("Unexpected error in main loop", e)
    finally:
        print("[PRINT] Stopping MQTT loop and disconnecting client.")
        client.loop_stop()
        client.disconnect()
        log("MQTT client disconnected.")

if __name__ == "__main__":
    main()
