from datetime import datetime
from flask import Blueprint, request, jsonify
from app.hr.routes import HR_ROLES, principal, require
from app.hr.service import HRError


def register_timesheet_routes(service,prefix):
    bp=Blueprint('timesheets',__name__)
    def allowed(username):
        actor=principal()
        if actor['role'] not in HR_ROLES and actor['username']!=username:raise HRError('Je kunt alleen je eigen uren bekijken.',403)
    @bp.route(prefix+'/timesheets/<username>')
    @require()
    def daily(username):
        allowed(username);date=datetime.strptime(request.args['date'],'%Y-%m-%d')
        return jsonify(success=True,data=service.get_user_timesheet_for_day(username,date))
    @bp.route(prefix+'/timesheets/<username>/range')
    @require()
    def period(username):
        allowed(username)
        start=datetime.strptime(request.args['start'],'%Y-%m-%d');end=datetime.strptime(request.args['end'],'%Y-%m-%d')
        return jsonify(success=True,data=service.get_user_timesheet_for_range(username,start,end))
    return bp
