#!/usr/bin/env python3
"""Seed demo users and badge logs through the backend API."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib import error, parse, request


DEMO_USERS = [
    {
        "first_name": "Piet",
        "last_name": "Jansen",
        "email": "piet.jansen@example.local",
        "username": "jansen.piet",
        "password": "demo123",
        "company_name": "Demo BV",
        "role": "user",
    },
    {
        "first_name": "Sanne",
        "last_name": "de Vries",
        "email": "sanne.devries@example.local",
        "username": "devries.sanne",
        "password": "welkom123",
        "company_name": "Demo BV",
        "role": "user",
    },
]

DEMO_BADGES = [
    {
        "badge_code": "BADGE-001",
        "action": "START",
        "username": "jansen.piet",
        "user_id": "jansen-piet-001",
        "first_name": "Piet",
        "last_name": "Jansen",
        "location": "Hoofdingang",
        "device_id": "reader-01",
        "raw_data": {"source": "seed_demo_via_api"},
    },
    {
        "badge_code": "BADGE-001",
        "action": "BREAK",
        "username": "jansen.piet",
        "user_id": "jansen-piet-001",
        "first_name": "Piet",
        "last_name": "Jansen",
        "location": "Kantine",
        "device_id": "reader-02",
        "raw_data": {"source": "seed_demo_via_api"},
    },
    {
        "badge_code": "BADGE-001",
        "action": "RETURN",
        "username": "jansen.piet",
        "user_id": "jansen-piet-001",
        "first_name": "Piet",
        "last_name": "Jansen",
        "location": "Kantine",
        "device_id": "reader-02",
        "raw_data": {"source": "seed_demo_via_api"},
    },
    {
        "badge_code": "BADGE-001",
        "action": "STOP",
        "username": "jansen.piet",
        "user_id": "jansen-piet-001",
        "first_name": "Piet",
        "last_name": "Jansen",
        "location": "Hoofdingang",
        "device_id": "reader-01",
        "raw_data": {"source": "seed_demo_via_api"},
    },
    {
        "badge_code": "BADGE-002",
        "action": "START",
        "username": "devries.sanne",
        "user_id": "devries-sanne-001",
        "first_name": "Sanne",
        "last_name": "de Vries",
        "location": "Hoofdingang",
        "device_id": "reader-01",
        "raw_data": {"source": "seed_demo_via_api"},
    },
    {
        "badge_code": "BADGE-002",
        "action": "STOP",
        "username": "devries.sanne",
        "user_id": "devries-sanne-001",
        "first_name": "Sanne",
        "last_name": "de Vries",
        "location": "Hoofdingang",
        "device_id": "reader-01",
        "raw_data": {"source": "seed_demo_via_api"},
    },
]


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


def ensure_user(client: ApiClient, user: dict[str, Any]) -> None:
    status, payload = client.request("POST", "/api/v1/users/", user)

    if status == 201:
        print(f"[OK] User created: {user['username']}")
        return

    message = str(payload.get("message", ""))
    if status == 400 and (
        "Username already exists" in message or "Email already exists" in message
    ):
        print(f"[SKIP] User already exists: {user['username']}")
        return

    raise RuntimeError(f"Could not create user {user['username']} ({status}): {payload}")


def cleanup_badges(client: ApiClient, username: str) -> None:
    status, payload = client.request(
        "GET",
        "/api/v1/badges/",
        query={
            "user": username,
            "start_date": "2026-03-21T00:00:00Z",
            "end_date": "2026-03-21T23:59:59Z",
            "limit": 100,
        },
    )
    if status != 200:
        raise RuntimeError(f"Could not list badges for {username} ({status}): {payload}")

    badges = payload.get("data", {}).get("badges", [])
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
    if badges:
        print(f"[CLEAN] Removed {len(badges)} existing badge logs for {username}")


def create_badges(client: ApiClient, badges: list[dict[str, Any]]) -> None:
    for badge in badges:
        status, payload = client.request("POST", "/api/v1/badges/", badge)
        if status != 201:
            raise RuntimeError(
                f"Could not create badge {badge['badge_code']} {badge['action']} "
                f"for {badge['username']} ({status}): {payload}"
            )
        print(f"[OK] Badge created: {badge['username']} - {badge['action']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed demo users and badge logs through the TimeTracking API.",
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
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    client = ApiClient(args.base_url)

    print(f"[INFO] Logging in at {args.base_url} as {args.admin_username}")
    client.login(args.admin_username, args.admin_password)

    for user in DEMO_USERS:
        ensure_user(client, user)

    for username in sorted({badge["username"] for badge in DEMO_BADGES}):
        cleanup_badges(client, username)

    create_badges(client, DEMO_BADGES)

    print("[DONE] Demo data seeded successfully via the API.")
    print("[DONE] Demo users: jansen.piet/demo123 and devries.sanne/welkom123")
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
