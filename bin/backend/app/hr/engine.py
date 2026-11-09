"""UTC interval calculation with local-day allocation; no database side effects."""
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
from zoneinfo import ZoneInfo

UTC = timezone.utc
ACTIONS = {'START', 'STOP', 'BREAK', 'RETURN', 'SCAN', 'SCAN_IN', 'SCAN_OUT'}
DEFAULT_RULES = {
    'timezone': 'Europe/Brussels', 'break_mode': 'recorded',
    'automatic_break_minutes': 0, 'automatic_break_after_minutes': 360,
    'max_open_hours': 16, 'auto_stop_mode': 'legacy_elapsed',
    'auto_stop_hours': 8, 'auto_stop_at': '17:00',
    'auto_stop_rule': 'elapsed', 'balance_alert_minutes': 0,
    'approval_required': True, 'allow_approval_with_anomalies': False,
    'notifications_enabled': True, 'export_delimiter': ';',
}


def instant(value):
    if isinstance(value, str): value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if not isinstance(value, datetime): raise ValueError('Ongeldig tijdstip; gebruik ISO 8601.')
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def iso(value): return instant(value).isoformat().replace('+00:00', 'Z')
def day(value): return date.fromisoformat(str(value)[:10])


def policy(state, on):
    versions = [p for p in state.get('policies', []) if p['effective_from'] <= str(on)]
    chosen = max(versions, key=lambda p: p['effective_from']) if versions else {}
    return {**DEFAULT_RULES, **chosen.get('rules', {}), 'timezone':state.get('timezone',DEFAULT_RULES['timezone'])}


def local_bounds(on, timezone_name):
    tz = ZoneInfo(timezone_name)
    return (datetime.combine(on, time.min, tz).astimezone(UTC),
            datetime.combine(on + timedelta(days=1), time.min, tz).astimezone(UTC))


def expected(state, employee, on):
    assignments = [a for a in state.get('assignments', [])
                   if a['employee_id'] == employee['id'] and a['effective_from'] <= str(on)]
    if not assignments: return None
    assignment = max(assignments, key=lambda a: a['effective_from'])
    schedule = next(s for s in state['schedules'] if s['id'] == assignment['schedule_id'])
    minutes = schedule['days'][on.weekday()]['minutes']
    # Explicit calendar entries override the base norm, without stacking deductions.
    entries = [c for c in state.get('calendar', []) if c['start'] <= str(on) <= c['end']
               and (not c.get('employee_id') or c['employee_id'] == employee['id'])
               and (not c.get('department') or c['department'] == employee.get('department'))]
    entries.sort(key=lambda c: bool(c.get('employee_id')))  # stable insertion order within specificity
    for entry in entries:
        if entry['effect'] == 'zero': minutes = 0
        elif entry['effect'] == 'hours': minutes = entry['minutes']
    return int(minutes * 60)


def effective_events(raw, corrections):
    records = {str(e['_id']): {**deepcopy(e), 'id': str(e['_id'])} for e in raw}
    for correction in corrections:
        value = correction['new']
        if value is None:
            records.pop(correction['target_id'], None)
        else:
            records[correction['target_id']] = {**deepcopy(value), 'id': correction['target_id'],
                '_id': correction['target_id'], '_correction_id': correction['id'],
                '_source': correction.get('source', 'manual')}
    return list(records.values())


def calculate(events, state, employee, start, end, now=None, as_of=None):
    now = instant(now or datetime.now(UTC))
    timezone_name = policy(state, start)['timezone']
    tz = ZoneInfo(timezone_name)
    today = now.astimezone(tz).date()
    cutoff = min(day(as_of) if as_of else today, today)
    horizon = min(now, local_bounds(min(end, cutoff), timezone_name)[1])
    days = {}
    bounds = {}
    current = start
    while current <= end:
        norm = expected(state, employee, current)
        days[str(current)] = {'date': str(current), 'expected_seconds': norm if current <= cutoff else 0,
            'full_expected_seconds': norm, 'work_seconds': 0, 'break_seconds': 0,
            'automatic_break_seconds': 0, 'periods': [], 'events': [], 'anomalies': [],
            'corrections': [], 'provisional': False, 'future': current > cutoff,
            'schedule_missing': norm is None, 'open_status': 'idle'}
        current += timedelta(days=1)
    bounds={key:local_bounds(day(key),timezone_name) for key in days}
    query_lo=bounds[str(start)][0]
    query_hi=bounds[str(end)][1]

    def anomaly(ts, code, text, event_id=None):
        key = str(instant(ts).astimezone(tz).date())
        if key in days:
            item = {'code': code, 'message': text, 'event_id': event_id}
            if item not in days[key]['anomalies']: days[key]['anomalies'].append(item)

    def interval(a, b, kind, provisional=False):
        if b <= a or b <= query_lo or a >= query_hi: return
        for key, row in days.items():
            lo, hi = bounds[key]
            left, right = max(a, lo), min(b, hi, horizon)
            if right <= left: continue
            seconds = int((right - left).total_seconds())
            row['work_seconds' if kind == 'work' else 'break_seconds'] += seconds
            row['periods'].append({'kind': kind, 'start': iso(left), 'end': iso(right),
                                   'seconds': seconds, 'provisional': provisional})
            row['provisional'] |= provisional

    parsed = []
    for event in events:
        try:
            ts = instant(event.get('timestamp'))
            action = str(event.get('action', '')).upper()
            if action not in ACTIONS:
                anomaly(ts, 'invalid_action', 'Onbekende registratieactie.', event.get('id'))
                continue
            if ts <= horizon: parsed.append((ts, str(event.get('id', event.get('_id', ''))), action, event))
        except (ValueError, TypeError):
            # Keep corrupt source records visible instead of substituting today's time.
            days[str(start)]['anomalies'].append({'code':'invalid_timestamp',
                'message':'Een bronregistratie heeft geen geldig tijdstip.', 'event_id':str(event.get('_id',''))})
    status, opened, open_event, session_started = 'idle', None, None, None
    for ts, ident, action, event in sorted(parsed, key=lambda e:(e[0], e[1])):
        action = {'SCAN_IN':'START', 'SCAN_OUT':'STOP'}.get(action, action)
        key = str(ts.astimezone(tz).date())
        source = event.get('_source') or ('automatic' if event.get('raw_data', {}).get('auto_stop') else 'physical')
        if key in days:
            row = days[key]
            row['events'].append({'id':ident, 'timestamp':iso(ts), 'action':action,
                'source':source, 'device_id':event.get('device_id',''), 'location':event.get('location',''),
                'badge_code':event.get('badge_code'), 'raw_data':event.get('raw_data', {}),
                'correction_id':event.get('_correction_id')})
            if source != 'physical': row['corrections'].append(ident)
            if source == 'automatic': anomaly(ts, 'automatic_stop', 'Automatisch afgesloten; controle vereist.', ident)
        if action == 'SCAN': continue
        if action == 'START':
            if status != 'idle': anomaly(ts, 'duplicate_start', 'Dubbele start zonder geldige stop.', ident)
            else: status, opened, open_event, session_started = 'working', ts, ident, ts
        elif action == 'BREAK':
            if status != 'working': anomaly(ts, 'invalid_break', 'Pauze zonder open werkperiode.', ident)
            else:
                interval(opened, ts, 'work'); status, opened = 'on_break', ts
        elif action == 'RETURN':
            if status != 'on_break': anomaly(ts, 'invalid_return', 'Hervatting zonder open pauze.', ident)
            else:
                interval(opened, ts, 'break'); status, opened = 'working', ts
        elif action == 'STOP':
            if status == 'idle': anomaly(ts, 'missing_start', 'Stop zonder start.', ident)
            else:
                interval(opened, ts, 'work' if status == 'working' else 'break')
                status, opened, open_event, session_started = 'idle', None, None, None
    if opened:
        interval(opened, horizon, 'work' if status == 'working' else 'break', True)
        for key, row in days.items():
            lo, hi = local_bounds(day(key), timezone_name)
            if hi > opened and lo < horizon:
                row['open_status'] = status
                if day(key) < today:
                    anomaly(max(opened, lo), 'missing_stop', 'Open sessie zonder afsluitende stop.', open_event)
                if (now-session_started).total_seconds() > policy(state, day(key))['max_open_hours']*3600:
                    anomaly(max(opened, lo), 'long_open', 'Open sessie langer dan de ingestelde grens.', open_event)
    for key, row in days.items():
        rules = policy(state, day(key))
        # Never deduct an automatic break in addition to actual recorded breaks.
        if rules['break_mode'] == 'automatic' and row['break_seconds'] == 0 and row['work_seconds'] >= rules['automatic_break_after_minutes']*60:
            deduction = min(row['work_seconds'], rules['automatic_break_minutes']*60)
            row['work_seconds'] -= deduction
            row['break_seconds'] += deduction
            row['automatic_break_seconds'] = deduction
        row['balance_seconds'] = None if row['expected_seconds'] is None else row['work_seconds']-row['expected_seconds']
        if row['expected_seconds'] and not row['events'] and not row['periods'] and day(key) <= cutoff and day(key) < today:
            row['anomalies'].append({'code':'no_registration', 'message':'Geen registratie op een verwachte werkdag.', 'event_id':None})
        if rules['balance_alert_minutes'] and row['balance_seconds'] is not None and abs(row['balance_seconds'])>rules['balance_alert_minutes']*60 and day(key)<cutoff:
            row['anomalies'].append({'code':'balance_alert','message':'Urensaldo overschrijdt de ingestelde signaleringsgrens.','event_id':None})
        row['status'] = ('afwijking' if row['anomalies'] else 'bezig' if row['provisional'] else
                         'afgesloten' if row['events'] or row['periods'] else 'geen_registratie')
        row['is_complete'] = row['status'] == 'afgesloten'
        row['net_work_seconds'] = row['work_seconds']
        row['work_hours_decimal'] = round(row['work_seconds']/3600, 4)
        row['break_hours_decimal'] = round(row['break_seconds']/3600, 4)
        row['errors'] = [a['message'] for a in row['anomalies']]
    result = list(days.values())
    def total(field): return sum(d[field] or 0 for d in result)
    missing_schedule = any(d['schedule_missing'] and not d['future'] for d in result)
    return {'days':result, 'summary':{
        'work_seconds':total('work_seconds'), 'break_seconds':total('break_seconds'),
        'expected_seconds':None if missing_schedule else total('expected_seconds'),
        'full_expected_seconds':None if any(d['schedule_missing'] for d in result) else total('full_expected_seconds'),
        'balance_seconds':None if missing_schedule else total('balance_seconds'),
        'anomaly_count':sum(len(d['anomalies']) for d in result),
        'provisional':any(d['provisional'] for d in result), 'schedule_missing':missing_schedule,
        'as_of':str(cutoff), 'automatic_count':sum(e['source']=='automatic' for d in result for e in d['events']),
    }}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(',', ':')).encode()).hexdigest()
