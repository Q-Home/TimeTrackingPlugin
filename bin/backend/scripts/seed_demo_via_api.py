#!/usr/bin/env python3
"""Seed richer demo users and badge logs through the backend API."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from urllib.parse import urlparse
from urllib import error, parse, request

try:
    from pymongo import MongoClient
except Exception:  # noqa: BLE001
    MongoClient = None


DEMO_USERS = [
    {
        "first_name": "Piet",
        "last_name": "Jansen",
        "email": "piet.jansen@example.local",
        "username": "jansen.piet",
        "password": "demo123",
        "company_name": "Demo BV",
        "role": "user",
        "badge_code": "BADGE-001",
        "user_id": "jansen-piet-001",
    },
    {
        "first_name": "Sanne",
        "last_name": "de Vries",
        "email": "sanne.devries@example.local",
        "username": "devries.sanne",
        "password": "welkom123",
        "company_name": "Demo BV",
        "role": "user",
        "badge_code": "BADGE-002",
        "user_id": "devries-sanne-001",
    },
    {
        "first_name": "Noah",
        "last_name": "Peeters",
        "email": "noah.peeters@example.local",
        "username": "peeters.noah",
        "password": "demo123",
        "company_name": "Demo BV",
        "role": "user",
        "badge_code": "BADGE-003",
        "user_id": "peeters-noah-001",
    },
    {
        "first_name": "Emma",
        "last_name": "Vermeulen",
        "email": "emma.vermeulen@example.local",
        "username": "vermeulen.emma",
        "password": "demo123",
        "company_name": "Demo BV",
        "role": "user",
        "badge_code": "BADGE-004",
        "user_id": "vermeulen-emma-001",
    },
    {
        "first_name": "Liam",
        "last_name": "Maes",
        "email": "liam.maes@example.local",
        "username": "maes.liam",
        "password": "demo123",
        "company_name": "Demo BV",
        "role": "user",
        "badge_code": "BADGE-005",
        "user_id": "maes-liam-001",
    },
    {
        "first_name": "Julie",
        "last_name": "Claes",
        "email": "julie.claes@example.local",
        "username": "claes.julie",
        "password": "demo123",
        "company_name": "Demo BV",
        "role": "user",
        "badge_code": "BADGE-006",
        "user_id": "claes-julie-001",
    },
]

LOCATIONS = {
    "office": "Hoofdingang",
    "canteen": "Kantine",
    "warehouse": "Magazijn",
}

DEVICES = {
    "office": "reader-01",
    "canteen": "reader-02",
    "warehouse": "reader-03",
}


@dataclass(frozen=True)
class UserPattern:
    start_hour: int
    start_minute: int
    workday_minutes: int
    break_minutes: int
    attendance: float
    uses_scan_actions: bool
    occasional_weekend: bool = False


USER_PATTERNS = {
    "jansen.piet": UserPattern(7, 42, 510, 34, 0.88, True),
    "devries.sanne": UserPattern(8, 24, 474, 42, 0.84, False),
    "peeters.noah": UserPattern(6, 58, 530, 27, 0.81, True, True),
    "vermeulen.emma": UserPattern(8, 51, 456, 30, 0.86, False),
    "maes.liam": UserPattern(7, 16, 562, 24, 0.79, True),
    "claes.julie": UserPattern(9, 5, 435, 36, 0.76, False),
}


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.token: str | None = None

    def _url(self, path: str, query: dict[str, Any] | None = None) -> str:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{parse.urlencode(query)}"
        return url

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        req = request.Request(
            self._url(path, query=query),
            data=data,
            headers=headers,
            method=method.upper(),
        )

        try:
            with request.urlopen(req) as response:
                body = response.read().decode("utf-8") or "{}"
                return response.status, json.loads(body)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8") or "{}"
            try:
                parsed = json.loads(body)
            except json.JSONDecodeError:
                parsed = {"message": body}
            return exc.code, parsed

    def login(self, username: str, password: str) -> None:
        status, payload = self.request(
            "POST",
            "/api/v1/login",
            {"username": username, "password": password},
        )
        if status != 200:
            raise RuntimeError(f"Login failed ({status}): {payload}")

        token = payload.get("data", {}).get("access_token")
        if not token:
            raise RuntimeError(f"Login succeeded but no token returned: {payload}")
        self.token = token


def get_error_message(payload: dict[str, Any]) -> str:
    return str(payload.get("error") or payload.get("message") or "")


def ensure_user(client: ApiClient, user: dict[str, Any]) -> None:
    payload = {
        "first_name": user["first_name"],
        "last_name": user["last_name"],
        "email": user["email"],
        "username": user["username"],
        "password": user["password"],
        "company_name": user["company_name"],
        "role": user["role"],
    }
    status, response_payload = client.request("POST", "/api/v1/users/", payload)

    if status == 201:
        print(f"[OK] User created: {user['username']}")
        return

    message = get_error_message(response_payload)
    if status == 400 and (
        "Username already exists" in message or "Email already exists" in message
    ):
        print(f"[SKIP] User already exists: {user['username']}")
        return

    raise RuntimeError(
        f"Could not create user {user['username']} ({status}): {response_payload}"
    )


def cleanup_badges(
    client: ApiClient,
    username: str,
    start_dt: datetime,
    end_dt: datetime,
) -> int:
    removed = 0
    page = 1

    while True:
        status, payload = client.request(
            "GET",
            "/api/v1/badges/",
            query={
                "user": username,
                "start_date": isoformat_utc(start_dt),
                "end_date": isoformat_utc(end_dt),
                "limit": 100,
                "page": page,
            },
        )
        if status != 200:
            raise RuntimeError(f"Could not list badges for {username} ({status}): {payload}")

        badges = payload.get("data", {}).get("badges", [])
        if not badges:
            break

        for badge in badges:
            badge_id = badge.get("id")
            if not badge_id:
                continue
            delete_status, delete_payload = client.request("DELETE", f"/api/v1/badges/{badge_id}")
            if delete_status != 200:
                raise RuntimeError(
                    f"Could not delete badge {badge_id} for {username} "
                    f"({delete_status}): {delete_payload}"
                )
            removed += 1

        if len(badges) < 100:
            break

    if removed:
        print(f"[CLEAN] Removed {removed} existing badge logs for {username}")
    return removed


def create_badges_via_api(client: ApiClient, badges: list[dict[str, Any]]) -> tuple[int, int]:
    total = len(badges)
    timestamp_fix_attempts = 0
    timestamp_fix_failures = 0

    for index, badge in enumerate(badges, start=1):
        status, payload = client.request("POST", "/api/v1/badges/", badge)
        if status != 201:
            raise RuntimeError(
                f"Could not create badge {badge['badge_code']} {badge['action']} "
                f"for {badge['username']} ({status}): {payload}"
            )

        created_badge = payload.get("data", {})
        created_badge_id = created_badge.get("id")
        created_timestamp = str(created_badge.get("timestamp") or "")
        expected_timestamp = badge["timestamp"]

        if created_badge_id and not same_timestamp_day(created_timestamp, expected_timestamp):
            timestamp_fix_attempts += 1
            if not force_badge_timestamp(client, created_badge_id, badge):
                timestamp_fix_failures += 1

        if index % 100 == 0 or index == total:
            print(f"[OK] Created {index}/{total} badge logs")

    if timestamp_fix_attempts:
        fixed = timestamp_fix_attempts - timestamp_fix_failures
        print(f"[INFO] Timestamp correction attempted for {timestamp_fix_attempts} badge logs, fixed {fixed}.")
    return timestamp_fix_attempts, timestamp_fix_failures


def same_timestamp_day(actual: str, expected: str) -> bool:
    if not actual or not expected:
        return False
    return actual[:10] == expected[:10]


def force_badge_timestamp(client: ApiClient, badge_id: str, badge: dict[str, Any]) -> bool:
    payload = {
        "timestamp": badge["timestamp"],
        "username": badge["username"],
        "user_id": badge["user_id"],
        "first_name": badge["first_name"],
        "last_name": badge["last_name"],
        "action": badge["action"],
        "location": badge["location"],
        "device_id": badge["device_id"],
    }
    status, update_payload = client.request("PUT", f"/api/v1/badges/{badge_id}", payload)
    if status != 200:
        print(
            f"[WARN] Could not correct timestamp for {badge['username']} {badge['action']} "
            f"({badge['timestamp']}): {get_error_message(update_payload) or update_payload}"
        )
        return False

    verify_status, verify_payload = client.request("GET", f"/api/v1/badges/{badge_id}")
    if verify_status != 200:
        print(
            f"[WARN] Could not verify corrected timestamp for {badge['username']} {badge['action']} "
            f"({badge['timestamp']})"
        )
        return False

    stored_timestamp = str(verify_payload.get("data", {}).get("timestamp") or "")
    if same_timestamp_day(stored_timestamp, badge["timestamp"]):
        return True

    print(
        f"[WARN] Timestamp still not applied for {badge['username']} {badge['action']}: "
        f"wanted {badge['timestamp']}, got {stored_timestamp or 'unknown'}"
    )
    return False


def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def resolve_mongo_uri(cli_value: str | None, base_url: str) -> str | None:
    if cli_value:
        return cli_value

    env_uri = os.getenv("MONGO_URI")
    if env_uri and "mongodb://mongodb:" not in env_uri:
        return env_uri

    host = urlparse(base_url).hostname
    if host:
        return f"mongodb://{host}:27017/timetracking"

    return None


def cleanup_badges_via_mongo(
    mongo_uri: str,
    usernames: list[str],
    start_dt: datetime,
    end_dt: datetime,
) -> int:
    if MongoClient is None:
        raise RuntimeError("pymongo is not installed, so Mongo fallback is unavailable")

    with MongoClient(mongo_uri) as mongo_client:
        collection = mongo_client.get_default_database()["badge_logs"]
        result = collection.delete_many(
            {
                "username": {"$in": usernames},
                "timestamp": {
                    "$gte": start_dt,
                    "$lte": end_dt,
                },
            }
        )
        return int(result.deleted_count)


def create_badges_via_mongo(mongo_uri: str, badges: list[dict[str, Any]]) -> None:
    if MongoClient is None:
        raise RuntimeError("pymongo is not installed, so Mongo fallback is unavailable")

    documents = []
    for badge in badges:
        timestamp = parse_timestamp(badge["timestamp"])
        documents.append(
            {
                "badge_code": badge["badge_code"],
                "action": badge["action"],
                "username": badge["username"],
                "user_id": badge["user_id"],
                "first_name": badge["first_name"],
                "last_name": badge["last_name"],
                "location": badge["location"],
                "device_id": badge["device_id"],
                "raw_data": badge["raw_data"],
                "processed": False,
                "timestamp": timestamp,
                "created_at": parse_timestamp(badge["created_at"]),
                "updated_at": parse_timestamp(badge["updated_at"]),
            }
        )

    with MongoClient(mongo_uri) as mongo_client:
        collection = mongo_client.get_default_database()["badge_logs"]
        if documents:
            collection.insert_many(documents, ordered=True)
    print(f"[OK] Inserted {len(documents)} badge logs directly into MongoDB")


def isoformat_utc(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def combine_day_time(day: date, hour: int, minute: int) -> datetime:
    return datetime.combine(day, time(hour=hour, minute=minute, tzinfo=UTC))


def is_work_day(day: date, pattern: UserPattern, rng: random.Random) -> bool:
    weekday = day.weekday()
    if weekday < 5:
        return rng.random() <= pattern.attendance
    if pattern.occasional_weekend and weekday == 5:
        return rng.random() <= 0.18
    return False


def action_names(pattern: UserPattern) -> tuple[str, str]:
    if pattern.uses_scan_actions:
        return "SCAN_IN", "SCAN_OUT"
    return "START", "STOP"


def maybe_break_minutes(pattern: UserPattern, rng: random.Random) -> int:
    if rng.random() < 0.18:
        return 0
    variation = rng.randint(-8, 12)
    return max(15, pattern.break_minutes + variation)


def maybe_work_minutes(pattern: UserPattern, day: date, rng: random.Random) -> int:
    variation = rng.randint(-55, 75)
    work_minutes = max(240, pattern.workday_minutes + variation)
    if day.weekday() == 4 and rng.random() < 0.35:
        work_minutes -= rng.randint(20, 60)
    if day.weekday() == 0 and rng.random() < 0.3:
        work_minutes += rng.randint(20, 70)
    return max(240, work_minutes)


def build_day_events(
    user: dict[str, Any],
    day: date,
    rng: random.Random,
) -> list[dict[str, Any]]:
    pattern = USER_PATTERNS[user["username"]]
    start_action, stop_action = action_names(pattern)

    start_dt = combine_day_time(day, pattern.start_hour, pattern.start_minute)
    start_dt += timedelta(minutes=rng.randint(-18, 24))

    break_minutes = maybe_break_minutes(pattern, rng)
    work_minutes = maybe_work_minutes(pattern, day, rng)

    events: list[tuple[str, datetime, str, str]] = []

    if break_minutes > 0:
        pre_break_minutes = max(110, min(work_minutes - 90, rng.randint(165, 245)))
        break_start = start_dt + timedelta(minutes=pre_break_minutes)
        break_end = break_start + timedelta(minutes=break_minutes)
        stop_dt = break_end + timedelta(minutes=max(60, work_minutes - pre_break_minutes))

        events.extend(
            [
                (start_action, start_dt, LOCATIONS["office"], DEVICES["office"]),
                ("BREAK", break_start, LOCATIONS["canteen"], DEVICES["canteen"]),
                ("RETURN", break_end, LOCATIONS["canteen"], DEVICES["canteen"]),
                (stop_action, stop_dt, LOCATIONS["office"], DEVICES["office"]),
            ]
        )
    else:
        stop_dt = start_dt + timedelta(minutes=work_minutes)
        stop_location = LOCATIONS["warehouse"] if rng.random() < 0.2 else LOCATIONS["office"]
        stop_device = DEVICES["warehouse"] if stop_location == LOCATIONS["warehouse"] else DEVICES["office"]
        events.extend(
            [
                (start_action, start_dt, LOCATIONS["office"], DEVICES["office"]),
                (stop_action, stop_dt, stop_location, stop_device),
            ]
        )

    if rng.random() < 0.06:
        events = events[:-1]

    payloads = []
    for action, timestamp, location, device_id in events:
        payloads.append(
            {
                "badge_code": user["badge_code"],
                "action": action,
                "username": user["username"],
                "user_id": user["user_id"],
                "first_name": user["first_name"],
                "last_name": user["last_name"],
                "location": location,
                "device_id": device_id,
                "timestamp": isoformat_utc(timestamp),
                "created_at": isoformat_utc(timestamp),
                "updated_at": isoformat_utc(timestamp),
                "raw_data": {
                    "source": "seed_demo_via_api",
                    "generated": True,
                    "scenario_date": day.isoformat(),
                },
            }
        )

    return payloads


def generate_badges(
    users: list[dict[str, Any]],
    days: int,
    seed: int,
    end_date: date,
) -> list[dict[str, Any]]:
    start_date = end_date - timedelta(days=days - 1)
    badges: list[dict[str, Any]] = []

    for user_index, user in enumerate(users):
        user_rng = random.Random(seed + (user_index * 1009))
        pattern = USER_PATTERNS[user["username"]]
        current_day = start_date

        while current_day <= end_date:
            if is_work_day(current_day, pattern, user_rng):
                badges.extend(build_day_events(user, current_day, user_rng))
            current_day += timedelta(days=1)

    badges.sort(key=lambda entry: (entry["timestamp"], entry["username"], entry["action"]))
    return badges


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed richer demo users and badge logs through the TimeTracking API.",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:5000",
        help="Base URL of the backend API, e.g. http://localhost:5000",
    )
    parser.add_argument(
        "--admin-username",
        default="admin",
        help="Admin username used to log in to the API",
    )
    parser.add_argument(
        "--admin-password",
        default="admin",
        help="Admin password used to log in to the API",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=75,
        help="How many calendar days of demo history to generate",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Deterministic seed for reproducible demo data",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Last date to generate in YYYY-MM-DD format, defaults to today (UTC)",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Do not remove existing badge logs for the seeded users in the target range first",
    )
    parser.add_argument(
        "--write-mode",
        choices=["auto", "api", "mongo"],
        default="auto",
        help="How badge logs should be written: via API, directly to MongoDB, or automatic fallback",
    )
    parser.add_argument(
        "--mongo-uri",
        default=None,
        help="MongoDB URI for direct writes, e.g. mongodb://localhost:27017/timetracking",
    )
    return parser.parse_args()


def resolve_end_date(value: str | None) -> date:
    if not value:
        return datetime.now(UTC).date()
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> int:
    args = parse_args()
    if args.days < 1:
        raise RuntimeError("--days must be at least 1")

    end_date = resolve_end_date(args.end_date)
    start_date = end_date - timedelta(days=args.days - 1)
    start_dt = datetime.combine(start_date, time.min, tzinfo=UTC)
    end_dt = datetime.combine(end_date, time.max, tzinfo=UTC)

    client = ApiClient(args.base_url)
    mongo_uri = resolve_mongo_uri(args.mongo_uri, args.base_url)
    usernames = [user["username"] for user in DEMO_USERS]

    print(f"[INFO] Logging in at {args.base_url} as {args.admin_username}")
    client.login(args.admin_username, args.admin_password)

    for user in DEMO_USERS:
        ensure_user(client, user)

    badges = generate_badges(DEMO_USERS, args.days, args.seed, end_date)
    use_mongo = args.write_mode == "mongo"

    if not args.no_cleanup:
        if use_mongo:
            if not mongo_uri:
                raise RuntimeError("No Mongo URI available for --write-mode mongo")
            removed = cleanup_badges_via_mongo(mongo_uri, usernames, start_dt, end_dt)
            if removed:
                print(f"[CLEAN] Removed {removed} existing badge logs via MongoDB")
        else:
            for user in DEMO_USERS:
                cleanup_badges(client, user["username"], start_dt, end_dt)

    if use_mongo:
        if not mongo_uri:
            raise RuntimeError("No Mongo URI available for --write-mode mongo")
        create_badges_via_mongo(mongo_uri, badges)
    else:
        attempts, failures = create_badges_via_api(client, badges)
        if failures:
            if args.write_mode == "api":
                raise RuntimeError(
                    "The backend ignored historical timestamps. "
                    "Restart the backend or rerun with --write-mode mongo."
                )
            if not mongo_uri:
                raise RuntimeError(
                    "The backend ignored historical timestamps and no Mongo URI is available for fallback."
                )
            print("[WARN] API kept saving timestamps on the wrong day. Replacing the seeded range directly in MongoDB.")
            removed = cleanup_badges_via_mongo(mongo_uri, usernames, start_dt, end_dt)
            if removed:
                print(f"[CLEAN] Removed {removed} API-inserted badge logs via MongoDB")
            create_badges_via_mongo(mongo_uri, badges)
        elif attempts:
            print("[INFO] Historical timestamps are now applied correctly.")

    print(
        f"[DONE] Seeded {len(DEMO_USERS)} users and {len(badges)} badge logs "
        f"from {start_date.isoformat()} to {end_date.isoformat()}."
    )
    print("[DONE] Example users: jansen.piet/demo123 and devries.sanne/welkom123")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n[ABORTED] Interrupted by user.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
