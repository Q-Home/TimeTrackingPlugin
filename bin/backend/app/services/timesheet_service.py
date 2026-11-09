"""Compatibility adapter: all timesheets use the shared HR calculation engine."""
from datetime import datetime
from flask import current_app
from app.hr.engine import calculate, day


class TimesheetService:
    def __init__(self,badge_repository):self.badge_repository=badge_repository
    def _normalize_action(self,action):return {'SCAN_IN':'START','SCAN_OUT':'STOP'}.get(str(action or '').upper(),str(action or '').upper())
    def calculate_day_timesheet(self,logs):
        dates=[day(e['timestamp']) for e in logs if isinstance(e.get('timestamp'),datetime)]
        target=min(dates) if dates else datetime.utcnow().date()
        return calculate(logs,{}, {'id':'legacy'},target,target)['days'][0]
    def details(self,username,start,end):
        hr=current_app.extensions['hr_service']
        employee=next((e for e in hr.employees(include_unresolved=True) if e['username']==username),None)
        if not employee:
            from app.hr.service import HRError
            raise HRError('Medewerker niet gevonden.',404)
        return hr.details(employee['id'],start.date(),end.date())
    def get_user_timesheet_for_day(self,username,day):
        result=self.details(username,day,day)
        return {'username':username,**result['days'][0],'total_logs':len(result['days'][0]['events'])}
    def get_user_timesheet_for_range(self,username,start_date,end_date):
        result=self.details(username,start_date,end_date);summary=result['summary']
        return {**result,'username':username,'summary':{**summary,
            'total_work_seconds':summary['work_seconds'],'total_break_seconds':summary['break_seconds'],
            'total_work_hours_decimal':round(summary['work_seconds']/3600,4),
            'total_break_hours_decimal':round(summary['break_seconds']/3600,4)}}
