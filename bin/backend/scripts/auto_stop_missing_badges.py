#!/usr/bin/env python3
"""Insert automatic STOP badge logs for users who forgot to badge out."""

from __future__ import annotations

import argparse
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from pymongo import MongoClient
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


BELGIUM_TZ = ZoneInfo("Europe/Brussels")
DEFAULT_WORK_HOURS = 8
DEFAULT_LOOKBACK_DAYS = 2
AUTO_LOCATION = "Automatisch systeem"
AUTO_DEVICE_ID = "auto-stop-cron"
PRESENT_ACTIONS = {"START", "RETURN", "SCAN_IN"}
EXIT_ACTIONS = {"STOP", "SCAN_OUT"}
VALID_ACTIONS = PRESENT_ACTIONS | EXIT_ACTIONS | {"BREAK"}


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def to_utc_naive(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)


def to_belgian(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=ZoneInfo("UTC")).astimezone(BELGIUM_TZ)
    return value.astimezone(BELGIUM_TZ)


def day_bounds_utc(target_day: datetime) -> tuple[datetime, datetime]:
    local_start = datetime(
        target_day.year,
        target_day.month,
        target_day.day,
        0,
        0,
        0,
        tzinfo=BELGIUM_TZ,
    )
    local_end = local_start + timedelta(days=1)
    return to_utc_naive(local_start), to_utc_naive(local_end)


def normalize_action(action: str | None) -> str:
    normalized = str(action or "").upper()
    if normalized == "SCAN_IN":
        return "START"
    if normalized == "SCAN_OUT":
        return "STOP"
    return normalized


def user_key(log: dict) -> tuple[str, str]:
    for field in ("username", "user_id", "badge_code"):
        value = str(log.get(field) or "").strip()
        if value:
            return field, value
    return "_id", str(log["_id"])


def find_open_sessions(logs: list[dict]) -> list[tuple[tuple[str, str], dict]]:
    grouped = defaultdict(list)
    for log in logs:
        grouped[user_key(log)].append(log)

    open_sessions = []
    for key, user_logs in grouped.items():
        open_start = None
        status = "idle"

        for log in sorted(user_logs, key=lambda item: item.get("timestamp") or datetime.min):
            action = normalize_action(log.get("action"))
            if action not in VALID_ACTIONS:
                continue

            if action == "START":
                open_start = log
                status = "working"
            elif action == "BREAK":
                if status == "working" and open_start:
                    status = "on_break"
            elif action == "RETURN":
                if open_start:
                    status = "working"
                else:
                    open_start = log
                    status = "working"
            elif action == "STOP":
                open_start = None
                status = "idle"

        if open_start and status != "idle":
            open_sessions.append((key, open_start))

    return open_sessions


def auto_stop_exists(collection, start_log: dict, stop_timestamp: datetime) -> bool:
    start_id = str(start_log["_id"])
    query = {
        "action": "STOP",
        "$or": [
            {"raw_data.auto_stop_start_id": start_id},
            {
                "username": start_log.get("username", ""),
                "timestamp": stop_timestamp,
                "device_id": AUTO_DEVICE_ID,
            },
        ],
    }
    return collection.count_documents(query, limit=1) > 0


def build_auto_stop(start_log: dict, stop_timestamp: datetime, run_time: datetime) -> dict:
    return {
        "badge_code": start_log.get("badge_code"),
        "action": "STOP",
        "username": start_log.get("username", ""),
        "user_id": start_log.get("user_id", ""),
        "first_name": start_log.get("first_name", ""),
        "last_name": start_log.get("last_name", ""),
        "location": AUTO_LOCATION,
        "device_id": AUTO_DEVICE_ID,
        "raw_data": {
            "auto_generated": True,
            "auto_stop": True,
            "reason": "missing_stop_badge",
            "note": "Gebruiker heeft niet zelf gestopt; STOP automatisch gezet op 8 uur na START.",
            "auto_stop_start_id": str(start_log["_id"]),
            "source": "auto_stop_missing_badges.py",
            "run_at": run_time.isoformat(),
        },
        "processed": False,
        "timestamp": stop_timestamp,
        "created_at": run_time,
        "updated_at": run_time,
    }


def run(collection, target_day: datetime, work_hours: int, lookback_days: int, dry_run: bool, hr_service=None) -> int:
    run_time = datetime.utcnow()
    inserted = 0

    for day_offset in range(max(lookback_days, 1) - 1, -1, -1):
        inserted += run_day(
            collection=collection,
            target_day=target_day - timedelta(days=day_offset),
            work_hours=work_hours,
            run_time=run_time,
            dry_run=dry_run,
            hr_service=hr_service,
        )

    return inserted


def run_day(collection, target_day: datetime, work_hours: int, run_time: datetime, dry_run: bool, hr_service=None) -> int:
    start_utc, end_utc = day_bounds_utc(target_day)
    logs = list(
        collection.find({"timestamp": {"$gte": start_utc, "$lt": end_utc}}).sort("timestamp", 1)
    )

    inserted = 0
    for _key, start_log in find_open_sessions(logs):
        stop_timestamp = start_log["timestamp"] + timedelta(hours=work_hours)
        mode = 'legacy_elapsed'
        if hr_service:
            from app.hr.engine import policy
            rules = policy(hr_service.state(), target_day.date())
            mode = rules['auto_stop_mode']
            if mode != 'legacy_elapsed':
                # New rules use the complete effective stream, including overnight
                # stops and HR overlays. Preserve the historical daily algorithm
                # only for installations that have not opted into a new policy.
                uid = hr_service.resolve(start_log)
                from app.hr.engine import instant
                later = sorted((e for e in hr_service.events(uid)
                                if instant(e['timestamp']) > instant(start_log['timestamp'])
                                and instant(e['timestamp']) <= instant(run_time)),
                               key=lambda e: instant(e['timestamp']))
                if any(normalize_action(e.get('action')) == 'STOP' for e in later):
                    continue
            if mode == 'signal':
                print('Open sessie gesignaleerd; geen automatische wijziging.')
                continue
            if mode != 'legacy_elapsed':
                if rules['auto_stop_rule'] == 'scheduled_end':
                    uid = hr_service.resolve(start_log)
                    state = hr_service.state()
                    assignments = [a for a in state['assignments'] if a['employee_id'] == uid and a['effective_from'] <= str(target_day.date())]
                    clock = rules['auto_stop_at']
                    if assignments:
                        assignment = max(assignments, key=lambda a:a['effective_from'])
                        schedule = next(s for s in state['schedules'] if s['id']==assignment['schedule_id'])
                        clock = schedule['days'][target_day.weekday()].get('end') or clock
                    hour, minute = map(int, clock.split(':'))
                    local = to_belgian(start_log['timestamp']).replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if to_utc_naive(local) <= start_log['timestamp']: local += timedelta(days=1)
                    stop_timestamp = to_utc_naive(local)
                else:
                    stop_timestamp = start_log['timestamp'] + timedelta(hours=rules['auto_stop_hours'])
            if mode == 'propose':
                hr_service.automatic_proposal(start_log, stop_timestamp, dry_run)
                continue
        if stop_timestamp > run_time:
            continue

        if auto_stop_exists(collection, start_log, stop_timestamp):
            continue

        auto_stop = build_auto_stop(start_log, stop_timestamp, run_time)
        if hr_service and mode != 'legacy_elapsed':
            auto_stop['raw_data'].update(reason='configured_auto_stop',
                note='Automatische STOP volgens de expliciet ingestelde afsluitregel.',rules_snapshot=rules)
        if dry_run:
            local_start = to_belgian(start_log["timestamp"]).isoformat()
            local_stop = to_belgian(stop_timestamp).isoformat()
            print(
                f"DRY RUN: would insert STOP for {start_log.get('username', '')}: "
                f"{local_start} -> {local_stop}"
            )
            inserted += 1
            continue

        token = None
        if hr_service:
            try: token = hr_service.reserve_event(auto_stop)
            except Exception:
                print('Automatische STOP niet toegepast: periodecontrole vereist.')
                continue
        try:
            collection.insert_one(auto_stop)
            inserted += 1
        finally:
            if token: hr_service.finish_event(token)

    return inserted


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Belgian date to process, YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--work-hours", type=int, default=DEFAULT_WORK_HOURS)
    parser.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    load_env_file(script_dir.parent / ".env")
    load_env_file(script_dir.parent.parent / ".env")

    args = build_parser().parse_args()
    target_day = (
        datetime.strptime(args.date, "%Y-%m-%d").replace(tzinfo=BELGIUM_TZ)
        if args.date
        else datetime.now(BELGIUM_TZ)
    )

    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/timetracking")
    db_name = os.getenv("MONGO_DB_NAME", "timetracking")
    client = MongoClient(mongo_uri)
    collection = client[db_name]["badge_logs"]

    from app.hr.service import HRService
    inserted = run(collection, target_day, args.work_hours, args.lookback_days, args.dry_run,
                   hr_service=HRService(client[db_name]))
    print(f"Automatic STOP badges {'would be inserted' if args.dry_run else 'inserted'}: {inserted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
