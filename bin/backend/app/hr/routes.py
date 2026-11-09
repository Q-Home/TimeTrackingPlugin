from functools import wraps
from datetime import datetime, timedelta, timezone
from bson import ObjectId
from flask import Blueprint, Response, current_app, g, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
from app.hr.engine import day, policy
from app.hr.service import HRError, clean

HR_ROLES={'admin','hr'}
TECH_ROLES={'admin','technical_admin'}


def principal():
    if getattr(g,'hr_principal',None):return g.hr_principal
    verify_jwt_in_request()
    service=current_app.extensions['hr_service']
    claims=get_jwt();uid=claims.get('employee_id')
    user=None
    if uid:
        try:user=service.db.users.find_one({'_id':ObjectId(uid)})
        except Exception:pass
    if not user:user=service.db.users.find_one({'username':get_jwt_identity()})
    if not user or user.get('blocked'):raise HRError('Je sessie is niet meer geldig. Meld opnieuw aan.',401)
    g.hr_principal={'id':str(user['_id']),'username':user['username'],'role':user.get('role','user')}
    return g.hr_principal


def require(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args,**kwargs):
            actor=principal()
            if roles and actor['role'] not in roles:raise HRError('Je hebt geen rechten voor deze handeling.',403)
            return fn(*args,**kwargs)
        return wrapped
    return decorator


def scoped(uid):
    actor=principal()
    if actor['role'] not in HR_ROLES and uid!=actor['id']:raise HRError('Je kunt alleen je eigen uren bekijken.',403)
    return actor


def register_hr_routes(service,prefix):
    bp=Blueprint('hr',__name__,url_prefix=prefix+'/hr')
    @bp.after_request
    def no_cache(response):
        response.headers['Cache-Control']='no-store'
        return response
    @bp.errorhandler(ValueError)
    @bp.errorhandler(KeyError)
    @bp.errorhandler(TypeError)
    def invalid_input(exc):
        return jsonify(success=False,error='Ongeldige of ontbrekende invoer. Controleer de datums, uren en verplichte velden.'),400
    def response(data,status=200):return jsonify({'success':True,'data':clean(data)}),status
    def payload():
        value=request.get_json(silent=True)
        if not isinstance(value,dict):raise HRError('Verstuur een geldig JSON-object.')
        return value
    def key():return request.headers.get('Idempotency-Key','')
    def actor():return principal()['username']
    def period_args():
        values=request.args.to_dict()
        values.setdefault('start',str(datetime.now(timezone.utc).date().replace(day=1)))
        values.setdefault('end',str(datetime.now(timezone.utc).date()))
        day(values['start']);day(values['end'])
        return values

    @bp.route('/me')
    @require()
    def me():
        user=principal()
        return response({**user,'can_hr':user['role'] in HR_ROLES,'can_technical':user['role'] in TECH_ROLES,
                         'revision':service.state()['revision'],'timezone':policy(service.state(),datetime.now(timezone.utc).date())['timezone']})

    @bp.route('/employees')
    @require(*HR_ROLES)
    def employees():return response(service.employees(include_unresolved=True))

    @bp.route('/overview')
    @require(*HR_ROLES)
    def overview():
        result=service.overview(period_args())
        page=max(1,int(request.args.get('page',1)));size=min(100,max(1,int(request.args.get('limit',25))))
        result['rows']=result['rows'][(page-1)*size:page*size]
        result.update(page=page,limit=size)
        return response(result)

    @bp.route('/details/<uid>')
    @require()
    def details(uid):
        scoped(uid);args=period_args()
        return response(service.details(uid,day(args['start']),day(args['end']),as_of=args.get('as_of')))

    @bp.route('/config')
    @require(*HR_ROLES)
    def config():return response(service.settings_view())

    @bp.route('/config/<kind>',methods=['POST'])
    @require(*HR_ROLES)
    def configure(kind):return response(service.setting(kind,payload(),actor(),key()))

    @bp.route('/corrections',methods=['POST'])
    @require(*HR_ROLES)
    def correct():
        data=payload();data.pop('_source',None)
        return response(service.correct(data,actor(),key()))

    @bp.route('/requests',methods=['POST'])
    @require()
    def correction_request():
        data=payload();uid=data.get('employee_id',principal()['id']);scoped(uid)
        return response(service.correction_request(data,actor(),uid,key()),201)

    @bp.route('/requests/reject',methods=['POST'])
    @require(*HR_ROLES)
    def reject():return response(service.reject_request(payload(),actor(),key()))

    @bp.route('/approvals',methods=['POST'])
    @require(*HR_ROLES)
    def approve():return response(service.approval(payload(),actor(),key()))

    @bp.route('/export')
    @require()
    def export():
        args=period_args()
        if principal()['role'] not in HR_ROLES:args['employee_id']=principal()['id']
        output=service.csv_export(args)
        return Response(output,content_type='text/csv; charset=utf-8',
            headers={'Content-Disposition':'attachment; filename="urenoverzicht.csv"','Cache-Control':'no-store'})

    @bp.route('/worklist')
    @require(*HR_ROLES)
    def worklist():
        args=period_args();state=service.state();result=[]
        for row in service.overview(args,state)['rows']:
            detail=service.details(row['employee']['id'],day(args['start']),day(args['end']),state,as_of=args.get('as_of'))
            for item in detail['days']:
                if item['anomalies']:result.append({'employee':row['employee'],'day':item})
        return response({'rows':result,'requests':[r for r in state['requests'] if r['status']=='open'],
                         'proposals':[p for p in state['proposals'] if p['status']=='open'],'revision':state['revision']})

    @bp.route('/dashboard')
    @require(*HR_ROLES)
    def dashboard():
        from zoneinfo import ZoneInfo
        now=datetime.now(timezone.utc);state=service.state()
        today=now.astimezone(ZoneInfo(policy(state,now.date())['timezone'])).date()
        args={'start':str(today-timedelta(days=30)),'end':str(today)}
        people=[];anomalies=automatic=pending=0;on_break=0
        for row in service.overview(args,state,now)['rows']:
            detail=service.details(row['employee']['id'],day(args['start']),today,state,now)
            last=detail['days'][-1]
            if last['provisional']:
                event=next((e for d in reversed(detail['days']) for e in reversed(d['events'])),{})
                people.append({'employee':row['employee'],'status':last['open_status'],
                    'last_registration_point':event.get('location') or event.get('device_id') or 'Onbekend'})
                on_break+=last['open_status']=='on_break'
            anomalies+=detail['summary']['anomaly_count']
            automatic+=sum(a['code']=='automatic_stop' and d['approval_status']=='te_controleren' for d in detail['days'] for a in d['anomalies'])
            pending+=policy(state,today)['approval_required'] and any(d['events'] and not d['provisional'] and d['approval_status']=='te_controleren' for d in detail['days'][:-1])
        return response({'clocked_in':len(people)-on_break,'on_break':on_break,'anomalies':anomalies,
            'automatic_to_review':automatic,'pending_approval':pending,'people':people,
            'window':args,'notifications_enabled':policy(state,today)['notifications_enabled']})

    @bp.route('/system')
    @require(*TECH_ROLES)
    def system():return response({'pending_ingest':service.state()['pending_ingest'],
        'revision':service.state()['revision']})

    @bp.route('/system/reconcile',methods=['POST'])
    @require(*TECH_ROLES)
    def reconcile():
        from copy import deepcopy
        from app.hr.engine import instant
        data=payload();reason=service.reason(data);before=service.state()
        if data.get('revision')!=before['revision']:raise HRError('Vernieuw eerst de verwerkingsstatus.',409)
        token=data['token'];pending=before['pending_ingest'].get(token)
        if not pending:raise HRError('Verwerkingssleutel niet gevonden.',404)
        stored=service.db.badge_logs.find_one({'_hr_ingest_id':token}) is not None
        if not stored and (datetime.now(timezone.utc)-instant(pending['at'])).total_seconds()<600:raise HRError('Deze registratie kan nog actief zijn. Wacht minstens tien minuten.',409)
        if not stored and not data.get('confirm_lost'):raise HRError('Bevestig expliciet dat de ontbrekende bronregistratie apart onderzocht wordt.')
        if not stored and not data.get('confirm_writer_stopped'):raise HRError('Bevestig eerst dat de uitvoerende backend is herstart of beëindigd; anders kan een late schrijfactie de periode nog veranderen.')
        state=deepcopy(before);del state['pending_ingest'][token]
        service.audit(state,actor(),'ingest_reconcile',pending,{'stored':stored},reason,pending['employee_id'],token)
        service.commit(before,state)
        return response({'revision':state['revision'],'stored':stored})

    return bp


def register_hr_errors(app):
    @app.errorhandler(HRError)
    def hr_error(exc):return jsonify({'success':False,'error':exc.message}),exc.status
