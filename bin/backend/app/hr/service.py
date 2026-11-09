"""Atomic HR control state for standalone MongoDB; raw badge events stay immutable.

Settings, correction overlays, approvals and audit are committed in one versioned
document. A revision compare-and-swap prevents lost writes. Ingestion reservations
fence approvals against in-flight badge writes (including two Gunicorn workers).
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import csv
import io
import json
import re
import uuid
from zoneinfo import ZoneInfo
from pymongo.errors import DuplicateKeyError
from app.hr.engine import (ACTIONS, DEFAULT_RULES, calculate, day, effective_events,
                           expected, fingerprint, instant, iso, local_bounds, policy)


class HRError(Exception):
    def __init__(self, message, status=400): self.message, self.status = message, status


def clean(value):
    if isinstance(value, dict): return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value, list): return [clean(v) for v in value]
    if isinstance(value, datetime): return iso(value)
    if value is None or isinstance(value, (str, int, float, bool)): return value
    return str(value)


def identifier(): return uuid.uuid4().hex
def timestamp(): return iso(datetime.now(timezone.utc))


class HRService:
    def __init__(self, db): self.db = db

    def state(self):
        return self.db.hr_state.find_one({'_id':'hr'}) or {
            '_id':'hr','revision':0,'schema_version':1,'schedules':[], 'assignments':[],
            'calendar':[], 'policies':[], 'corrections':[], 'requests':[],
            'approvals':[], 'audit':[], 'operations':{}, 'identity_links':{},
            'profiles':{}, 'pending_ingest':{}, 'proposals':[],
        }

    def employees(self, state=None, include_unresolved=False):
        state = state or self.state()
        result = []
        users=list(self.db.users.find({}))
        for user in users:
            uid = str(user['_id'])
            profile = state['profiles'].get(uid, {})
            result.append({'id':uid, 'username':user.get('username',''),
                'name':profile.get('name') or ' '.join(filter(None,[user.get('first_name'),user.get('last_name')])) or user.get('username',''),
                'personnel_number':profile.get('personnel_number',user.get('personnel_number','')),
                'department':profile.get('department',user.get('department','')),
                'role':user.get('role','user'), 'unresolved':False})
        if include_unresolved:
            known = {e['id'] for e in result}
            for event in self.db.badge_logs.find({}, {'password':0}):
                uid = self.resolve(event,state,users)
                if uid not in known:
                    result.append({'id':uid,'username':event.get('username',''),
                        'name':event.get('username') or event.get('user_id') or 'Onopgeloste historische identiteit',
                        'personnel_number':'','department':'','unresolved':True, 'role':'unknown',
                        'identity_key':self.identity_key(event)})
                    known.add(uid)
        return sorted(result,key=lambda e:e['name'].casefold())

    @staticmethod
    def identity_key(event):
        if event.get('username'): return 'username:'+str(event['username'])
        if event.get('user_id'): return 'external:'+str(event['user_id'])
        return 'event:'+str(event.get('_id','unknown'))

    def resolve(self, event, state=None, users=None):
        state = state or self.state()
        if event.get('employee_id'): return str(event['employee_id'])
        key = self.identity_key(event)
        if key in state['identity_links']: return state['identity_links'][key]
        query = {'username':event['username']} if event.get('username') else {'user_id':event.get('user_id')} if event.get('user_id') else None
        candidates = [u for u in users if all(u.get(k)==v for k,v in query.items())] if query and users is not None else list(self.db.users.find(query)) if query else []
        if len(candidates)==1: return str(candidates[0]['_id'])
        return 'unresolved:'+fingerprint(key)[:20]

    def employee(self, uid, state=None):
        for employee in self.employees(state,True):
            if employee['id']==uid: return employee
        raise HRError('Medewerker niet gevonden.',404)

    def events(self, uid, state=None):
        state = state or self.state()
        # Existing installations are small; filtering also resolves legacy aliases.
        users=list(self.db.users.find({}, {'username':1,'user_id':1}))
        raw = [e for e in self.db.badge_logs.find({}) if self.resolve(e,state,users)==uid]
        corrections = [c for c in state['corrections'] if c['employee_id']==uid]
        return effective_events(raw,corrections)

    def details(self, uid, start, end, state=None, now=None, as_of=None):
        state = state or self.state()
        if end < start or (end-start).days > 366: raise HRError('Kies een periode van maximaal 367 dagen.')
        employee = self.employee(uid,state)
        result = calculate(self.events(uid,state),state,employee,start,end,now,as_of)
        approvals = [a for a in state['approvals'] if a['employee_id']==uid and a['status'] in {'approved','closed'}]
        for row in result['days']:
            covering = [a for a in approvals if a['start']<=row['date']<=a['end']]
            row['approval_status'] = 'afgesloten' if any(a['status']=='closed' for a in covering) else 'goedgekeurd' if covering else 'te_controleren'
            for approval in covering:
                if approval['fingerprint']!=self.calculation_hash(uid,day(approval['start']),day(approval['end']),state):
                    row['approval_status']='bron_gewijzigd'
                    row['anomalies'].append({'code':'approval_source_changed','message':'Brongegevens wijken af van de goedgekeurde momentopname.','event_id':None})
            if covering: row['status'] = 'afwijking' if row['approval_status']=='bron_gewijzigd' else 'goedgekeurd'
        covering = [a for a in approvals if a['start']<=str(start) and a['end']>=str(end)]
        result['approval_status'] = 'afgesloten' if any(a['status']=='closed' for a in covering) else 'goedgekeurd' if covering else 'te_controleren'
        if any(d['approval_status']=='bron_gewijzigd' for d in result['days']):
            result['approval_status']='bron_gewijzigd'
        result['summary']['anomaly_count']=sum(len(d['anomalies']) for d in result['days'])
        result.update(employee=employee,start=str(start),end=str(end),revision=state['revision'])
        result['requests'] = [r for r in state['requests'] if r['employee_id']==uid]
        result['approvals'] = [a for a in state['approvals'] if a['employee_id']==uid]
        result['audit'] = [a for a in state['audit'] if a.get('employee_id')==uid]
        return result

    def overview(self, args, state=None, now=None):
        state = state or self.state()
        start,end = day(args['start']),day(args['end'])
        if end<start or (end-start).days>366: raise HRError('Kies een periode van maximaal 367 dagen.')
        rows=[]
        for employee in self.employees(state,True):
            if employee['role'] not in {'user','unknown'} and employee['id'] not in state['profiles'] and not any(a['employee_id']==employee['id'] for a in state['assignments']) and not self.events(employee['id'],state):
                continue
            if args.get('employee_id') and args['employee_id']!=employee['id']: continue
            if args.get('department') and args['department']!=employee['department']: continue
            detail = self.details(employee['id'],start,end,state,now,args.get('as_of'))
            status=detail['approval_status']
            control='goedgekeurd' if status in {'goedgekeurd','afgesloten'} else 'afwijking' if detail['summary']['anomaly_count'] else 'bezig' if detail['summary']['provisional'] else 'afgesloten' if detail['summary']['work_seconds'] else 'geen_registratie'
            if args.get('status') and args['status'] not in {'alle',status,control}: continue
            if args.get('anomalies')=='true' and not detail['summary']['anomaly_count']: continue
            rows.append({'employee':employee,**detail['summary'],'approval_status':status,'control_status':control})
        totals={k:sum(r[k] or 0 for r in rows) for k in ('work_seconds','break_seconds','anomaly_count','expected_seconds','balance_seconds')}
        if any(r['expected_seconds'] is None for r in rows):totals['expected_seconds']=totals['balance_seconds']=None
        return {'rows':rows,'total':len(rows),'totals':totals,'revision':state['revision'],'start':str(start),'end':str(end)}

    def audit(self,state,actor,kind,old,new,reason,uid=None,reference=None):
        state['audit'].append({'id':identifier(),'kind':kind,'old':clean(old),'new':clean(new),
            'reason':reason,'actor':actor,'at':timestamp(),'employee_id':uid,'reference':reference})

    def commit(self, previous, updated):
        updated['revision']=previous['revision']+1
        if len(json.dumps(clean(updated)).encode()) > 12_000_000:
            raise HRError('HR-historiek bereikt de opslaggrens. Archiveer gecontroleerd met behoud van de audit; er is niets verwijderd.',507)
        try:
            result=self.db.hr_state.replace_one({'_id':'hr','revision':previous['revision']},updated,upsert=previous['revision']==0)
        except DuplicateKeyError:
            raise HRError('De gegevens zijn ondertussen gewijzigd. Vernieuw en probeer opnieuw.',409)
        if result.matched_count==0 and not result.upserted_id:
            raise HRError('De gegevens zijn ondertussen gewijzigd. Vernieuw en probeer opnieuw.',409)
        from app.loxone_sync.bridge import notify_change
        notify_change(self.db)
        return updated

    def mutate(self,data,actor,kind,operation,key):
        if not key or not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',key): raise HRError('Een unieke Idempotency-Key van 8 tot 128 veilige tekens is verplicht.')
        before=self.state()
        digest=fingerprint([data,actor,kind])
        if key in before['operations']:
            saved=before['operations'][key]
            if saved['hash']!=digest: raise HRError('Deze aanvraagsleutel is al voor andere gegevens gebruikt.',409)
            return {**saved['result'],'revision':before['revision'],'replayed':True}
        if data.get('revision')!=before['revision']: raise HRError('De gegevens zijn gewijzigd. Vernieuw eerst.',409)
        if before['pending_ingest']: raise HRError('Een registratie wordt verwerkt. Probeer opnieuw zodra die afgerond is.',409)
        state=deepcopy(before)
        result=operation(state) or {}
        result['revision']=before['revision']+1
        state['operations'][key]={'hash':digest,'result':result}
        self.commit(before,state)
        return result

    @staticmethod
    def reason(data):
        value=str(data.get('reason','')).strip()
        if len(value)<3 or len(value)>2000: raise HRError('Geef een reden van 3 tot 2000 tekens.')
        return value

    def guard(self,state,start,end,uid=None,invalidate=False,actor=None,reason=''):
        for approval in state['approvals']:
            if uid and approval['employee_id']!=uid: continue
            if approval['start']>str(end) or approval['end']<str(start): continue
            if approval['status']=='closed': raise HRError('Deze wijziging raakt een afgesloten periode. Heropen die eerst met reden.',409)
            if approval['status']=='approved':
                if not invalidate: raise HRError('Deze wijziging raakt goedgekeurde uren. Trek de goedkeuring eerst expliciet in.',409)
                old=deepcopy(approval);approval['status']='invalidated'
                self.audit(state,actor,'approval_invalidated',old,approval,reason,approval['employee_id'],approval['id'])

    def guard_event_changes(self,state,uid,before_events,after_events,invalidate=False,actor=None,reason=''):
        employee=self.employee(uid,state)
        for approval in state['approvals']:
            if approval['employee_id']!=uid or approval['status'] not in {'approved','closed'}:continue
            args=(state,employee,day(approval['start']),day(approval['end']))
            before=calculate(before_events,*args,as_of=approval['end'])
            after=calculate(after_events,*args,as_of=approval['end'])
            if fingerprint(before)==fingerprint(after):continue
            if approval['status']=='closed':raise HRError('Deze wijziging raakt een afgesloten periode. Heropen die eerst met reden.',409)
            if not invalidate:raise HRError('Trek de betrokken goedkeuring expliciet in voordat je corrigeert.',409)
            old=deepcopy(approval);approval['status']='invalidated'
            self.audit(state,actor,'approval_invalidated',old,approval,reason,uid,approval['id'])

    def setting(self,kind,data,actor,key):
        reason=self.reason(data)
        def apply(state):
            uid=data.get('employee_id')
            if kind=='schedule':
                value=data['schedule'];name=str(value.get('name','')).strip()
                days=value.get('days')
                if not name or len(name)>100 or not isinstance(days,list) or len(days)!=7: raise HRError('Een rooster heeft een naam en zeven weekdagen nodig.')
                for entry in days:
                    minutes=entry.get('minutes')
                    if isinstance(minutes,bool) or not isinstance(minutes,(int,float)) or not 0<=minutes<=1440: raise HRError('Roosteruren moeten tussen 0 en 24 per dag liggen.')
                    for field in ('start','end'):
                        if entry.get(field):
                            try: datetime.strptime(entry[field],'%H:%M')
                            except (ValueError,TypeError): raise HRError('Gebruik HH:MM voor roostertijden.')
                value={'id':identifier(),'name':name,'days':deepcopy(days)}
                state['schedules'].append(value);old=None
            elif kind=='assignment':
                if self.employee(uid,state)['unresolved']: raise HRError('Koppel eerst de historische identiteit.')
                effective=str(day(data['effective_from']))
                if not any(s['id']==data['schedule_id'] for s in state['schedules']): raise HRError('Rooster niet gevonden.')
                self.guard(state,effective,'9999-12-31',uid)
                old=[a for a in state['assignments'] if a['employee_id']==uid and a['effective_from']==effective]
                state['assignments']=[a for a in state['assignments'] if a not in old]
                value={'id':identifier(),'employee_id':uid,'schedule_id':data['schedule_id'],'effective_from':effective}
                state['assignments'].append(value)
            elif kind=='calendar':
                begin,end=str(day(data['start'])),str(day(data['end']))
                if end<begin or data.get('kind') not in {'holiday','closure','absence'} or data.get('effect') not in {'zero','keep','hours'}: raise HRError('Ongeldige kalenderinstelling.')
                if data['kind']=='absence' and not uid: raise HRError('Kies een medewerker voor afwezigheid.')
                if uid:self.employee(uid,state)
                self.guard(state,begin,end,uid)
                minutes=data.get('minutes',0)
                if not isinstance(minutes,(int,float)) or not 0<=minutes<=1440:raise HRError('Ongeldige kalenderuren.')
                value={'id':identifier(),'start':begin,'end':end,'kind':data['kind'],'effect':data['effect'],
                    'minutes':minutes,'employee_id':uid,'department':str(data.get('department','')),'label':str(data.get('label',''))[:200]}
                old=None;state['calendar'].append(value)
            elif kind=='calendar_remove':
                value=next((c for c in state['calendar'] if c['id']==data['id']),None)
                if not value:raise HRError('Kalenderregel niet gevonden.',404)
                self.guard(state,value['start'],value['end'],value.get('employee_id'))
                old=deepcopy(value);state['calendar'].remove(value)
                value={'id':data['id'],'removed':True}
            elif kind=='policy':
                effective=str(day(data['effective_from']));rules={**DEFAULT_RULES,**data['rules']}
                if set(rules)!=set(DEFAULT_RULES):raise HRError('Onbekende berekeningsinstelling.')
                try:ZoneInfo(rules['timezone'])
                except Exception:raise HRError('Onbekende tijdzone.')
                if state.get('timezone') and rules['timezone']!=state['timezone']:raise HRError('Tijdzone wijzigen vereist een afzonderlijke migratie.')
                if rules['timezone']!=policy(state,day(effective))['timezone']:
                    self.guard(state,'0001-01-01','9999-12-31')
                state['timezone']=rules['timezone']
                if rules['break_mode'] not in {'recorded','automatic'} or rules['auto_stop_mode'] not in {'legacy_elapsed','signal','propose','automatic'}:raise HRError('Ongeldige pauze- of afsluitregel.')
                if rules['auto_stop_rule'] not in {'elapsed','scheduled_end'}:raise HRError('Ongeldige automatische eindtijdregel.')
                for field,lo,hi in [('automatic_break_minutes',0,720),('automatic_break_after_minutes',1,1440),('max_open_hours',1,168),('auto_stop_hours',0.25,24),('balance_alert_minutes',0,10080)]:
                    if isinstance(rules[field],bool) or not isinstance(rules[field],(int,float)) or not lo<=rules[field]<=hi:raise HRError('Ongeldige waarde voor '+field+'.')
                for field in ('approval_required','allow_approval_with_anomalies','notifications_enabled'):
                    if not isinstance(rules[field],bool):raise HRError('Gebruik aan/uit voor '+field+'.')
                try:datetime.strptime(rules['auto_stop_at'],'%H:%M')
                except (ValueError,TypeError):raise HRError('Ongeldige voorgestelde eindtijd.')
                if rules['export_delimiter'] not in {';',','}:raise HRError('CSV-scheidingsteken moet een komma of puntkomma zijn.')
                self.guard(state,effective,'9999-12-31')
                old=[p for p in state['policies'] if p['effective_from']==effective]
                state['policies']=[p for p in state['policies'] if p not in old]
                value={'id':identifier(),'effective_from':effective,'rules':rules};state['policies'].append(value)
            elif kind=='profile':
                self.employee(uid,state);self.guard(state,'0001-01-01','9999-12-31',uid)
                old=state['profiles'].get(uid)
                value={k:str(data.get(k,''))[:120] for k in ('name','personnel_number','department')}
                state['profiles'][uid]=value
            elif kind=='identity':
                employee=self.employee(uid,state)
                if employee['unresolved']:raise HRError('Kies een bestaand medewerkersaccount.')
                self.guard(state,'0001-01-01','9999-12-31')
                identity=data['identity_key']
                if not identity.startswith(('username:','external:','event:')):raise HRError('Ongeldige historische sleutel.')
                old=state['identity_links'].get(identity);state['identity_links'][identity]=uid
                value={'identity_key':identity,'employee_id':uid}
            else:raise HRError('Onbekende instelling.')
            self.audit(state,actor,kind,old,value,reason,uid,value.get('id'))
            return {'value':value}
        return self.mutate(data,actor,kind,apply,key)

    def correct(self,data,actor,key):
        reason=self.reason(data);uid=data['employee_id']
        def apply(state):
            self.employee(uid,state)
            events=self.events(uid,state)
            target=data.get('target_id') or 'manual:'+identifier()
            old=next((e for e in events if str(e.get('id',e.get('_id')))==target),None)
            if data.get('target_id') and not old:raise HRError('Registratie niet gevonden.',404)
            new=data.get('new')
            if new is None and not old:raise HRError('Geen registratie om te laten vervallen.')
            if new is not None:
                if set(new)-{'action','timestamp','local_time','fold','location','device_id'}:raise HRError('De correctie bevat niet-toegestane velden.')
                if new.get('local_time'):
                    tz=ZoneInfo(policy(state,day(new['local_time']))['timezone'])
                    naive=datetime.fromisoformat(new['local_time'])
                    if naive.tzinfo is not None:raise HRError('Gebruik een lokale datum en tijd zonder offset bij local_time.')
                    candidates=[naive.replace(tzinfo=tz,fold=f) for f in (0,1)]
                    valid=[c for c in candidates if c.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None)==naive]
                    if not valid:raise HRError('Dit tijdstip bestaat niet door de overgang naar zomertijd.')
                    if len({c.utcoffset() for c in valid})>1 and new.get('fold') not in (0,1):raise HRError('Dit wintertijdstip komt tweemaal voor. Kies het eerste of tweede uur.')
                    new={**new,'timestamp':iso(naive.replace(tzinfo=tz,fold=new.get('fold') or 0))}
                if new.get('action') not in ACTIONS:raise HRError('Ongeldige registratieactie.')
                try:ts=iso(new['timestamp'])
                except (ValueError,TypeError,KeyError):raise HRError('Een tijdstip met tijdzone is verplicht.')
                if isinstance(new['timestamp'],str) and datetime.fromisoformat(new['timestamp'].replace('Z','+00:00')).tzinfo is None:raise HRError('Geef een expliciete tijdzone of UTC Z op.')
                new={**clean(old or {}),**new,'timestamp':ts,'employee_id':uid}
            correction={'id':identifier(),'employee_id':uid,'target_id':target,'old':clean(old),
                'new':clean(new),'reason':reason,'actor':actor,'at':timestamp(),'source':data.get('_source','manual')}
            state['corrections'].append(correction)
            self.guard_event_changes(state,uid,events,self.events(uid,state),bool(data.get('invalidate_approval')),actor,reason)
            if data.get('proposal_id'):
                proposal=next((p for p in state['proposals'] if p['id']==data['proposal_id'] and p['employee_id']==uid and p['status']=='open'),None)
                if not proposal:raise HRError('Voorstel niet gevonden of al behandeld.',409)
                proposal.update(status='approved',correction_id=correction['id'])
            if data.get('request_id'):
                request=next((r for r in state['requests'] if r['id']==data['request_id'] and r['employee_id']==uid and r['status']=='open'),None)
                if not request:raise HRError('Correctieaanvraag bestaat niet of is al behandeld.',409)
                request['status']='approved';request['correction_id']=correction['id']
            self.audit(state,actor,'correction',old,new,reason,uid,target)
            return {'correction':correction}
        return self.mutate(data,actor,'correction',apply,key)

    def correction_request(self,data,actor,uid,key):
        reason=self.reason(data)
        def apply(state):
            self.employee(uid,state)
            value={'id':identifier(),'employee_id':uid,'reason':reason,'proposed':data.get('proposed',{}),
                'target_id':data.get('target_id'),'status':'open','actor':actor,'at':timestamp()}
            state['requests'].append(value);self.audit(state,actor,'correction_request',None,value,reason,uid,value['id'])
            return {'request':value}
        return self.mutate(data,actor,'request',apply,key)

    def reject_request(self,data,actor,key):
        reason=self.reason(data)
        def apply(state):
            records=state['proposals'] if data.get('proposal_id') else state['requests']
            reference=data.get('proposal_id') or data.get('request_id')
            record=next((r for r in records if r['id']==reference and r['status']=='open'),None)
            if not record:raise HRError('Open aanvraag niet gevonden.',404)
            old=deepcopy(record);record.update(status='rejected',resolution_reason=reason,resolved_by=actor)
            self.audit(state,actor,'request_rejected',old,record,reason,record['employee_id'],record['id'])
            return {'request':record}
        return self.mutate(data,actor,'reject_request',apply,key)

    def approval(self,data,actor,key):
        reason=self.reason(data);uid=data['employee_id'];start,end=day(data['start']),day(data['end'])
        action=data['action']
        def apply(state):
            if start>end:raise HRError('Ongeldige periode.')
            item=next((a for a in state['approvals'] if a['employee_id']==uid and a['start']==str(start) and a['end']==str(end)),None)
            old=deepcopy(item)
            if action=='approve':
                self.guard(state,start,end,uid)
                detail=self.details(uid,start,end,state)
                rules=policy(state,start)
                if end>=datetime.now(timezone.utc).astimezone(ZoneInfo(rules['timezone'])).date():raise HRError('Keur alleen volledig verstreken dagen goed.')
                if detail['employee']['unresolved'] or detail['summary']['schedule_missing']:raise HRError('Koppel de identiteit en stel eerst een rooster in.')
                if detail['summary']['provisional']:raise HRError('Sluit open sessies af voordat je goedkeurt.')
                if detail['summary']['anomaly_count'] and not rules['allow_approval_with_anomalies']:raise HRError('Behandel eerst de afwijkingen of wijzig de expliciete goedkeuringsregel.')
                value={'id':item['id'] if item else identifier(),'employee_id':uid,'start':str(start),'end':str(end),
                    'status':'approved','actor':actor,'at':timestamp(),'fingerprint':self.calculation_hash(uid,start,end,state)}
                if item:state['approvals'].remove(item)
                state['approvals'].append(value)
            elif action in {'close','reopen','invalidate'}:
                if not item:raise HRError('Goedkeuring niet gevonden.',404)
                if action=='close' and item['status']!='approved':raise HRError('Keur de periode eerst goed.',409)
                if action=='close' and item['fingerprint']!=self.calculation_hash(uid,start,end,state):raise HRError('Brongegevens zijn gewijzigd; de goedkeuring is niet meer geldig.',409)
                if action=='reopen' and item['status']!='closed':raise HRError('Deze periode is niet afgesloten.',409)
                if action=='invalidate' and item['status']=='closed':raise HRError('Heropen eerst de afgesloten periode.',409)
                item['status']={'close':'closed','reopen':'reopened','invalidate':'invalidated'}[action]
                item['changed_by']=actor;item['changed_at']=timestamp();value=item
            else:raise HRError('Onbekende goedkeuringsactie.')
            self.audit(state,actor,'period_'+action,old,value,reason,uid,value['id'])
            return {'approval':value}
        return self.mutate(data,actor,'period_'+action,apply,key)

    def calculation_hash(self,uid,start,end,state):
        result=calculate(self.events(uid,state),state,self.employee(uid,state),start,end,as_of=str(end))
        return fingerprint(result)

    def reserve_event(self,event):
        from bson import ObjectId
        event.setdefault('_id',ObjectId())
        for _ in range(12):
            before=self.state();state=deepcopy(before);uid=self.resolve(event,state)
            event['employee_id']=uid if not uid.startswith('unresolved:') else None
            date_key=str(instant(event['timestamp']).astimezone(ZoneInfo(policy(state,day(event['timestamp']))['timezone'])).date())
            if not uid.startswith('unresolved:'):
                current=self.events(uid,state)
                self.guard_event_changes(state,uid,current,current+[{**event,'id':str(event['_id'])}],True,'system:ingest','Nieuwe bronregistratie')
            token=identifier();event['_hr_ingest_id']=token
            state['pending_ingest'][token]={'employee_id':uid,'date':date_key,'at':timestamp()}
            try:self.commit(before,state);return token
            except HRError as exc:
                if exc.status!=409:raise
        raise HRError('Registratie is druk bezet. Probeer opnieuw.',409)

    def finish_event(self,token):
        for _ in range(20):
            before=self.state()
            if token not in before['pending_ingest']:return
            state=deepcopy(before);del state['pending_ingest'][token]
            try:self.commit(before,state);return
            except HRError as exc:
                if exc.status!=409:raise
        raise HRError('Registratie opgeslagen maar verwerking is nog niet afgerond.',409)

    def remember_username(self,old,new,uid):
        if old==new:return
        for _ in range(12):
            before=self.state();state=deepcopy(before)
            for name in (old,new):
                existing=state['identity_links'].get('username:'+name)
                if existing and existing!=str(uid):
                    raise HRError('Deze gebruikersnaam is gekoppeld aan een andere historische medewerker. Kies een nieuwe naam.',409)
            state['identity_links']['username:'+old]=str(uid)
            state['identity_links']['username:'+new]=str(uid)
            try:self.commit(before,state);return
            except HRError as exc:
                if exc.status!=409:raise
        raise HRError('Gebruikersnaam is ondertussen gewijzigd. Probeer opnieuw.',409)

    def settings_view(self,state=None):
        state=state or self.state()
        return {'revision':state['revision'],'schedules':state['schedules'],'assignments':state['assignments'],
            'calendar':state['calendar'],'policies':state['policies'],'rules':policy(state,datetime.now(timezone.utc).date()),
            'profiles':state['profiles'],'pending_ingest':state['pending_ingest'],
            'requests':state['requests'],'approvals':state['approvals'],'proposals':state['proposals']}

    def automatic_proposal(self,event,stop_time,dry_run=False):
        if dry_run:return
        for _ in range(12):
            before=self.state();state=deepcopy(before);uid=self.resolve(event,state)
            reference=fingerprint([str(event['_id']),iso(stop_time)])[:32]
            if any(p['id']==reference for p in state['proposals']):return
            value={'id':reference,'employee_id':uid,'start_event_id':str(event['_id']),
                'new':{'action':'STOP','timestamp':iso(stop_time)},'status':'open','at':timestamp()}
            state['proposals'].append(value)
            self.audit(state,'system:auto_stop','auto_stop_proposed',None,value,'Voorstel volgens ingestelde afsluitregel',uid,reference)
            try:self.commit(before,state);return
            except HRError as exc:
                if exc.status!=409:raise
        raise HRError('Voorstel kon door gelijktijdige wijzigingen nog niet worden vastgelegd.',409)

    def csv_export(self,args,now=None):
        state=self.state();overview=self.overview(args,state,now)
        buffer=io.StringIO(newline='');delimiter=policy(state,day(args['start']))['export_delimiter']
        writer=csv.writer(buffer,delimiter=delimiter)
        writer.writerow(['Personeelsnummer','Naam','Afdeling','Medewerker-ID','Periode van','Periode tot','Datum',
            'Verwacht HH:MM','Netto HH:MM','Pauze HH:MM','Urensaldo HH:MM','Verwacht seconden','Netto seconden',
            'Pauze seconden','Urensaldo seconden','Afwijkingen','Controlestatus','Goedkeuring','Voorlopig','Herkomst',
            'Volledige dagnorm HH:MM','Volledige dagnorm seconden'])
        def duration(value):
            if value is None:return ''
            return ('-' if value<0 else '')+f'{abs(int(value))//3600:02}:{abs(int(value))%3600//60:02}'
        def safe(value):
            value=str(value or '')
            return "'"+value if value[:1] in {'=','+','-','@','\t','\r'} else value
        for employee in [r['employee'] for r in overview['rows']]:
            details=self.details(employee['id'],day(args['start']),day(args['end']),state,now,args.get('as_of'))
            for row in details['days']:
                sources=sorted(set(e['source'] for e in row['events']))
                writer.writerow([safe(employee['personnel_number']),safe(employee['name']),safe(employee['department']),
                    employee['id'],args['start'],args['end'],row['date'],duration(row['expected_seconds']),duration(row['work_seconds']),
                    duration(row['break_seconds']),duration(row['balance_seconds']),row['expected_seconds'],row['work_seconds'],
                    row['break_seconds'],row['balance_seconds'],len(row['anomalies']),row['status'],row['approval_status'],row['provisional'],','.join(sources),
                    duration(row['full_expected_seconds']),row['full_expected_seconds']])
        return '\ufeff'+buffer.getvalue()
