# ---------------- Imports ----------------
import os
import time
from datetime import datetime
from pymongo import MongoClient
import paho.mqtt.client as mqtt

# ---------------- Configuration ----------------
DB_FOLDER = "/opt/loxberry/data/plugins/timetracking-plugin"
DB_NAME = os.getenv("MONGO_DB_NAME", "timetracking")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION_NAME", "entrees")
LOGFILE = os.path.join(DB_FOLDER, "timetracking_mqtt.log")

# MongoDB connection - configureerbaar via environment variables
MONGO_URI = os.getenv("MONGO_URI", "mongodb://192.168.0.137:27017/")
MONGO_HOST = os.getenv("MONGO_HOST", "192.168.0.137")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))

# MQTT settings - configureerbaar
MQTT_BROKER = os.getenv("MQTT_BROKER", "192.168.0.100")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "miniserver/timetracking")
MQTT_STATS_TOPIC = os.getenv(
    "MQTT_STATS_TOPIC", "miniserver/timetracking/getstats")
MQTT_PUB_TOPIC = os.getenv("MQTT_PUB_TOPIC", "loxberry/timetracking")
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "loxberry")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "loxberry")

# ---------------- Logging Function ----------------


def log(msg):
    print(f"[{datetime.now()}] {msg}")
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    with open(LOGFILE, "a") as f:
        f.write(f"[{datetime.now()}] {msg}\n")

# ---------------- MongoDB Operations ----------------


def insert_to_db(badgecode, user, scan_time, status, action="none"):
    try:
        log(f"Connecting to MongoDB at {MONGO_URI}...")
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        collection.insert_one({
            "badgecode": badgecode,
            "user": user,
            "scan_time": scan_time,
            "status": status,
            "action": action
        })
        log(f"Inserted into MongoDB: badgecode='{badgecode}', user='{user}', scan_time='{scan_time}', status='{status}', action='{action}'")
    except Exception as e:
        log(f"Database error: {e}")
    finally:
        try:
            client.close()
            log("MongoDB connection closed.")
        except Exception as e:
            log(f"Error closing MongoDB connection: {e}")


def get_user_logs(username):
    logs = []
    try:
        log(f"Fetching logs for user: {username}")
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        logs = list(collection.find({"user": username}))
        log(f"Found {len(logs)} logs for {username}")
    except Exception as e:
        log(f"Database query error: {e}")
    finally:
        try:
            client.close()
        except:
            pass
    return logs

# ---------------- MQTT Publishing ----------------


def publish_to_loxone(client, badgecode, user, scan_time, status):
    if status == "granted":
        message = f"{badgecode},{user},{scan_time},{status}"
    else:
        message = f"{scan_time},{status}"
    try:
        log(f"Publishing to Loxone MQTT: {message}")
        client.publish(MQTT_PUB_TOPIC, message)
    except Exception as e:
        log(f"Failed to publish to Loxone MQTT: {e}")

# ---------------- MQTT Callbacks ----------------


def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        log("Connected to MQTT broker successfully.")
        client.subscribe(MQTT_TOPIC)
        client.subscribe(MQTT_STATS_TOPIC)
        log(f"Subscribed to topics: {MQTT_TOPIC} and {MQTT_STATS_TOPIC}")
    else:
        log(f"Failed to connect to MQTT broker, return code {rc}")


def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip()
    topic = msg.topic
    log(f"Received MQTT message on topic '{topic}': {payload}")

    if topic == MQTT_TOPIC:
        scan_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if payload == "Access Denied":
            log("Processing 'Access Denied' message.")
            insert_to_db("", "", scan_time, "Access Denied", "none")
            publish_to_loxone(client, "", "", scan_time, "Access Denied")
        else:
            parts = payload.split(";")
            if len(parts) >= 4:
                badgecode = parts[0].strip()
                user = parts[1].strip()
                scan_time = parts[2].strip()
                action = parts[3].strip().lower()  # 'start' or 'stop'
                log(
                    f"Processing 'Access Granted': badgecode={badgecode}, user={user}, scan_time={scan_time}, action={action}")
                insert_to_db(badgecode, user, scan_time,
                             "Access Granted", action)
                publish_to_loxone(client, badgecode, user,
                                  scan_time, "Access Granted")
            else:
                log(f"Ignored malformed message: {payload}")

    elif topic == MQTT_STATS_TOPIC:
        try:
            parts = payload.split(";")
            if len(parts) != 1:
                log(f"Invalid payload for stats request: {payload}")
                return
            username = parts[0].strip()
            log(f"Stats requested for user '{username}'")

            logs = get_user_logs(username)
            if logs:
                log(f"Found {len(logs)} logs for user '{username}'")
                # Logs gevonden - je kunt hier andere acties ondernemen als je wilt
                # Bijvoorbeeld: verstuur terug via MQTT of sla op in een speciaal logbestand
            else:
                log(f"No logs found for user: {username}")
        except Exception as e:
            log(f"Error handling stats request: {e}")

# ---------------- Main Loop ----------------


def main():
    log("Starting timetracking MQTT script...")
    log(f"MongoDB URI: {MONGO_URI}")
    log(f"MQTT Broker: {MQTT_BROKER}:{MQTT_PORT}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        log(f"Connecting to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except Exception as e:
        log(f"MQTT connection error: {e}")
        return

    client.loop_start()
    log("MQTT loop started.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("KeyboardInterrupt: Shutting down gracefully.")
    except Exception as e:
        log(f"Unexpected error in main loop: {e}")
    finally:
        client.loop_stop()
        client.disconnect()
        log("MQTT client disconnected.")


if __name__ == "__main__":
    main()
