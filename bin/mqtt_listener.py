# ---------------- Imports ----------------
import os
import time
from datetime import datetime
from pymongo import MongoClient
import paho.mqtt.client as mqtt

# ---------------- Configuration ----------------
DB_FOLDER = "/opt/loxberry/data/plugins/timetracking-plugin"
DB_NAME = "timetracking"
COLLECTION_NAME = "devices"
LOGFILE = os.path.join(DB_FOLDER, "timetracking_mqtt.log")

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "miniserver/timetracking"
MQTT_PUB_TOPIC = "loxberry/timetracking"

# ---------------- Logging Function ----------------
def log(msg):
    os.makedirs(os.path.dirname(LOGFILE), exist_ok=True)
    with open(LOGFILE, "a") as f:
        f.write(f"[{datetime.now()}] {msg}\n")

# ---------------- MongoDB Operations ----------------
def insert_to_db(badgecode, user, scan_time, status):
    try:
        client = MongoClient("mongodb://localhost:27017/")
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        collection.insert_one({
            "badgecode": badgecode,
            "user": user,
            "scan_time": scan_time,
            "status": status
        })
        log(f"Inserted: badgecode='{badgecode}', user='{user}', scan_time='{scan_time}', status='{status}'")
    except Exception as e:
        log(f"Database error: {e}")
    finally:
        client.close()

# ---------------- MQTT Publishing ----------------
def publish_to_loxone(client, badgecode, user, scan_time, status):
    if status == "granted":
        message = f"{badgecode},{user},{scan_time},{status}"
    else:
        message = f"{scan_time},{status}"
    try:
        client.publish(MQTT_PUB_TOPIC, message)
        log(f"Published to Loxone MQTT: {message}")
    except Exception as e:
        log(f"Failed to publish to Loxone MQTT: {e}")

# ---------------- MQTT Callbacks ----------------
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        log("Connected to MQTT broker successfully.")
        client.subscribe(MQTT_TOPIC)
        log(f"Subscribed to topic: {MQTT_TOPIC}")
    else:
        log(f"Failed to connect to MQTT broker, return code {rc}")

def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip()
    log(f"Received MQTT message: {payload}")

    scan_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if payload == "Access Denied":
        insert_to_db("", "", scan_time, "Access Denied")
        publish_to_loxone(client, "", "", scan_time, "Access Denied")
        log("Logged access denied")
    else:
        parts = payload.split(";")
        if len(parts) >= 3:
            badgecode = parts[0].strip()
            user = parts[1].strip()
            scan_time = parts[2].strip()
            insert_to_db(badgecode, user, scan_time, "Access Granted")
            publish_to_loxone(client, badgecode, user, scan_time, "Access Granted")
        else:
            log(f"Ignored malformed message: {payload}")

# ---------------- Main Loop ----------------
def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set("loxberry", "loxberry")
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    except Exception as e:
        log(f"MQTT connection error: {e}")
        return

    client.loop_start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Shutting down gracefully.")
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
