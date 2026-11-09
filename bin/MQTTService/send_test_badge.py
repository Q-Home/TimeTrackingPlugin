import argparse
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import paho.mqtt.client as mqtt


def get_belgium_tz():
    try:
        return ZoneInfo("Europe/Brussels")
    except ZoneInfoNotFoundError:
        # Windows Python may not have tzdata installed; fall back to local timezone.
        return datetime.now().astimezone().tzinfo


BELGIUM_TZ = get_belgium_tz()


def build_parser():
    parser = argparse.ArgumentParser(
        description="Simulate a timetracking badge event and publish it over MQTT."
    )
    parser.add_argument("--broker", default=os.getenv("MQTT_BROKER", "192.168.19.119"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument("--topic", default=os.getenv("MQTT_TOPIC", "miniserver/timetracking"))
    parser.add_argument("--username-auth", default=os.getenv("MQTT_USERNAME", "loxberry"))
    parser.add_argument("--password-auth", default=os.getenv("MQTT_PASSWORD", ""))
    parser.add_argument("--badge-code", default="")
    parser.add_argument("--username", default="example.user")
    parser.add_argument("--user-id", default="example-user")
    parser.add_argument("--first-name", default="")
    parser.add_argument("--last-name", default="")
    parser.add_argument("--action", default="START")
    parser.add_argument("--location", default="Voordeur")
    parser.add_argument("--device-id", default="Code_Touch_001")
    parser.add_argument("--scan-time", default="")
    parser.add_argument("--status", default="Access Granted")
    return parser


def main():
    args = build_parser().parse_args()
    scan_time = args.scan_time or datetime.now(BELGIUM_TZ).isoformat()

    payload = {
        "badge_code": args.badge_code,
        "username": args.username,
        "user_id": args.user_id,
        "first_name": args.first_name,
        "last_name": args.last_name,
        "action": args.action,
        "location": args.location,
        "device_id": args.device_id,
        "status": args.status,
        "scan_time": scan_time,
    }

    print(f"Connecting to MQTT broker {args.broker}:{args.port} on topic '{args.topic}'")
    print(f"Publishing payload: {json.dumps(payload, ensure_ascii=True)}")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    if args.username_auth:
        client.username_pw_set(args.username_auth, args.password_auth)

    client.connect(args.broker, args.port, keepalive=60)
    result = client.publish(args.topic, json.dumps(payload))
    result.wait_for_publish()
    client.disconnect()

    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        raise SystemExit(f"Publish failed with rc={result.rc}")

    print("Message published successfully.")


if __name__ == "__main__":
    main()
