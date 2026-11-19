"""One cron-driven writer, coalesced notifications and current-state retries."""
from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import re
import uuid
from zoneinfo import ZoneInfo
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from app.hr.engine import calculate, instant, iso, policy
from app.hr.service import HRError, clean
from .bridge import Bridge, SyncError, MESSAGES, TRANSPORT_WARNINGS

FIELDS=tuple('customField'+str(i) for i in range(1,6))
METRICS={'none','today','week','month','balance','status','updated'}
UNRELIABLE={'duplicate_start','invalid_break','invalid_return','missing_start','missing_stop',
    'long_open','invalid_action','invalid_timestamp','automatic_stop','approval_source_changed','no_registration'}


def clock(): return datetime.now(timezone.utc)
def duration(seconds,signed=False):
    minutes=int(abs(seconds)//60)
    return ('−' if seconds<0 else '+' if signed else '')+f'{minutes//60}u {minutes%60:02}m'


class SyncService:
    def __init__(self, db, hr, bridge=None):
        self.db,self.hr=db,hr
        self.bridge=bridge or Bridge(warning_handler=self.record_transport)

    def record_transport(self,server,warnings):
        if not isinstance(server,dict) or not re.fullmatch(r'[0-9]{1,4}',str(server.get('slot',''))):return
        codes=[w for w in warnings if isinstance(w,str) and w in TRANSPORT_WARNINGS]
        try:
            self.db.loxone_sync_meta.update_one({'_id':'transport:'+str(server['slot'])},
                {'$set':{'checked_at':clock(),'warnings':codes}},upsert=True)
        except Exception:
            pass  # A diagnostic write must not turn a successful Miniserver call into a failure.

    def transport_status(self,server):
        if not server:return {'warnings':[]}
        saved=self.db.loxone_sync_meta.find_one({'_id':'transport:'+str(server['slot'])}) or {}
        return {'checked_at':saved.get('checked_at'),'warnings':[{'code':w,'message':TRANSPORT_WARNINGS[w]}
            for w in saved.get('warnings',[]) if isinstance(w,str) and w in TRANSPORT_WARNINGS]}

    def config(self):
        defaults={
            '_id':'settings','revision':0,'enabled':False,'server':None,'interval':600,
            'mapping':{f:'none' for f in FIELDS},'bindings':{},'auto_link':True}
        config={**defaults,**(self.db.loxone_sync_config.find_one({'_id':'settings'}) or {})}
        # Apply the ten-minute floor to existing installations as well.
        config['interval']=max(600,config['interval'])
        return config

    @staticmethod
    def identity_key(value):
        if isinstance(value,bool) or not isinstance(value,(str,int)):raise SyncError('identity_conflict')
        text=str(value).strip()
        if not text or len(text)>128 or any(ord(c)<32 for c in text):raise SyncError('identity_conflict')
        if re.fullmatch(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-(?:[0-9a-f]{16}|[0-9a-f]{4}-[0-9a-f]{12})',text,re.I):
            return 'uuid:'+text.replace('-','').lower()
        return 'id:'+text

    def source_identity(self,user):
        values=[user['user_id']] if user.get('user_id') not in (None,'') else []
        # Legacy manually created staff may have the ID only on their badge events.
        values += [e['user_id'] for e in self.hr.events(str(user['_id'])) if e.get('user_id') not in (None,'')]
        if not values:return None
        keys={self.identity_key(value) for value in values}
        if len(keys)!=1:raise SyncError('identity_conflict')
        return str(values[0]).strip()

    def automatic_links(self,config,owner):
        if not config['auto_link'] or not config['server']:return config,{}
        users=list(self.db.users.find({'archived':{'$ne':True},'blocked':{'$ne':True}}))
        sources={};errors={};groups={}
        for user in users:
            uid=str(user['_id'])
            try:
                source=self.source_identity(user)
                if source:
                    sources[uid]=source;groups.setdefault(self.identity_key(source),[]).append(uid)
            except SyncError as exc:errors[uid]=exc.code
        for matches in groups.values():
            if len(matches)>1:
                errors.update({uid:'identity_conflict' for uid in matches})
        new=deepcopy(config);changes=[]
        for uid,source in sources.items():
            if uid in errors:continue
            previous=config['bindings'].get(uid)
            # UUIDs are stable. Numeric/text userid mappings are re-resolved each
            # sweep, so reassigning an ID cannot silently redirect someone’s hours.
            if previous and previous.get('matched_by')=='loxone_id' and self.identity_key(source).startswith('uuid:') and self.identity_key(previous['source_id'])==self.identity_key(source):
                self.db.loxone_sync_meta.update_one({'_id':'identity:'+uid},{'$set':{'source_id':source,'error_code':None,'at':clock()}},upsert=True)
                continue
            try:
                self.renew(owner)
                remote=self.bridge.call('resolve',config['server'],userid=source)
                if not isinstance(remote,dict) or not isinstance(remote.get('name'),str) or not remote.get('uuid'):raise SyncError('identity_conflict')
                if self.identity_key(remote['uuid']).split(':',1)[0]!='uuid' or self.identity_key(remote.get('source_id',''))!=self.identity_key(source):raise SyncError('identity_conflict')
                if self.identity_key(source).startswith('uuid:') and self.identity_key(source)!=self.identity_key(remote['uuid']):raise SyncError('identity_conflict')
                if previous and self.identity_key(previous['uuid'])!=self.identity_key(remote['uuid']):raise SyncError('identity_conflict')
                collisions=[other for other,binding in new['bindings'].items() if other!=uid and self.identity_key(binding['uuid'])==self.identity_key(remote['uuid'])]
                if collisions:
                    errors.update({other:'identity_conflict' for other in collisions})
                    raise SyncError('identity_conflict')
                binding={'uuid':remote['uuid'],'name':remote['name'],'lookup_name':'','server':config['server'],
                         'matched_by':'loxone_id','source_id':source}
                if binding!=previous:
                    new['bindings'][uid]=binding;changes.append((uid,previous,binding))
                self.db.loxone_sync_meta.update_one({'_id':'identity:'+uid},{'$set':{'source_id':source,'error_code':None,'at':clock()}},upsert=True)
            except SyncError as exc:errors[uid]=exc.code
        for uid,code in errors.items():
            self.db.loxone_sync_meta.update_one({'_id':'identity:'+uid},{'$set':{'source_id':sources.get(uid),'error_code':code,'at':clock()}},upsert=True)
        if changes:
            self.renew(owner);new['revision']+=1
            self.db.loxone_sync_config.replace_one({'_id':'settings'},new,upsert=True)
            for uid,old,binding in changes:
                self.audit('system:loxone-id','automatic_binding',old,binding,'Automatisch gekoppeld via de Loxone-gebruikers-ID')
            self.request_sync('system:loxone-id')
        return new,errors

    @contextmanager
    def lock(self, now=None):
        now=now or clock(); owner=uuid.uuid4().hex
        try:
            record=self.db.loxone_sync_meta.find_one_and_update(
                {'_id':'lock','$or':[{'until':{'$lte':now}},{'until':{'$exists':False}}]},
                {'$set':{'owner':owner,'until':now+timedelta(minutes=15)}},upsert=True,
                return_document=ReturnDocument.AFTER)
        except DuplicateKeyError: raise SyncError('busy') from None
        if not record or record['owner']!=owner: raise SyncError('busy')
        try: yield owner
        finally: self.db.loxone_sync_meta.delete_one({'_id':'lock','owner':owner})

    def renew(self, owner):
        now=clock()
        result=self.db.loxone_sync_meta.update_one({'_id':'lock','owner':owner,'until':{'$gt':now}},
            {'$set':{'until':now+timedelta(minutes=15)}})
        if not result.matched_count: raise SyncError('busy')

    def audit(self,actor,kind,old,new,reason):
        self.db.loxone_sync_audit.insert_one({'at':clock(),'actor':actor,'kind':kind,
            'old':clean(old),'new':clean(new),'reason':reason})

    def save(self,data,actor):
        with self.lock():
            old=self.config()
            if data.get('revision')!=old['revision']:raise HRError('Instellingen gewijzigd. Vernieuw eerst.',409)
            reason=self.hr.reason(data)
            enabled=data.get('enabled')
            mapping=data.get('mapping')
            if not isinstance(enabled,bool) or not isinstance(mapping,dict) or set(mapping)!=set(FIELDS) or any(v not in METRICS for v in mapping.values()):
                raise HRError('Kies voor elk custom field een geldige toewijzing.')
            interval=data.get('interval')
            if isinstance(interval,bool) or not isinstance(interval,int) or not 600<=interval<=3600:
                raise HRError('Kies een synchronisatie-interval van 600 tot 3600 seconden.')
            server=data.get('server')
            if server is not None and (not isinstance(server,dict) or set(server)!={'slot','serial'} or not all(isinstance(v,str) and v for v in server.values())):
                raise HRError('Kies een geteste Miniserver uit LoxBerry.')
            changed=server!=old['server'] or mapping!=old['mapping']
            active=[f for f,v in mapping.items() if v!='none']
            if enabled:
                if not server or not any(v not in {'none','updated'} for v in mapping.values()):
                    raise HRError('Selecteer een Miniserver en minstens één inhoudelijk uren- of statusveld.')
                if (changed or not old['enabled']) and data.get('owned_fields')!=active:
                    raise HRError('Bevestig expliciet welke velden de plugin mag beheren na het bekijken van de bestaande waarden.')
                self.bridge.call('probe',server)
            new={**old,'enabled':enabled,'server':server,'interval':interval,'mapping':mapping,'revision':old['revision']+1}
            if server!=old['server']:new['bindings']={}
            self.db.loxone_sync_config.replace_one({'_id':'settings'},new,upsert=True)
            self.audit(actor,'configuration',old,new,reason)
            self.request_sync(actor)
            return new

    def probe(self,slot):
        if not re.fullmatch(r'[0-9]{1,4}',str(slot)):raise HRError('Kies een Miniserver uit de lijst.')
        return self.bridge.call('probe',{'slot':str(slot)})

    def remote_users(self):
        config=self.config()
        if not config['server']:raise HRError('Sla eerst een geteste Miniserverselectie op.')
        return self.bridge.call('users',config['server'])

    def link(self,data,actor):
        with self.lock():
            old=self.config()
            if data.get('revision')!=old['revision']:raise HRError('Instellingen gewijzigd. Vernieuw eerst.',409)
            if not old['server']:raise HRError('Kies eerst een Miniserver.')
            uid=data['employee_id']; employee=self.hr.employee(uid)
            if employee['unresolved']:raise HRError('Los eerst de interne historische identiteit op.')
            reason=self.hr.reason(data)
            existing=old['bindings'].get(uid)
            if existing and not data.get('replace'):
                raise HRError('Deze medewerker heeft al een UUID. Vervangen vereist een expliciete her-koppeling met reden.',409)
            users=self.bridge.call('users',old['server'])
            name=str(data.get('loxone_username') or employee['username']).strip()
            if data.get('uuid'):
                matches=[u for u in users if u['uuid']==data['uuid']]
            else:matches=[u for u in users if u['name']==name]
            if len(matches)!=1:raise HRError('Geen unieke exacte overeenkomst. Selecteer handmatig een bestaande Loxone-gebruiker.',409)
            user=matches[0]
            if any(k!=uid and b['uuid']==user['uuid'] for k,b in old['bindings'].items()):
                raise HRError('Deze Loxone-gebruiker is al aan een andere medewerker gekoppeld.',409)
            binding={'uuid':user['uuid'],'name':user['name'],'lookup_name':name,'server':old['server']}
            new=deepcopy(old);new['bindings'][uid]=binding;new['revision']+=1
            self.db.loxone_sync_config.replace_one({'_id':'settings'},new,upsert=True)
            self.db.loxone_sync_status.delete_one({'_id':uid})
            self.audit(actor,'binding',existing,binding,reason)
            self.request_sync(actor)
            return new

    def totals(self,uid,now=None):
        now=instant(now or clock());state=self.hr.state()
        simple=bool(state.get('simple_mode'))
        tz=ZoneInfo(policy(state,now.date())['timezone']);today=now.astimezone(tz).date()
        starts={'today':today,'week':today-timedelta(days=today.weekday()),'month':today.replace(day=1)}
        values={};issues={};provisional={}
        details={}
        for metric,start in starts.items():
            result=self.hr.details(uid,start,today,state,now,str(today));details[metric]=result
            warnings=[a['message'] for d in result['days'] for a in d['anomalies']+d.get('notes',[])]
            bad=[a['message'] for d in result['days'] for a in d['anomalies'] if a['code'] in ({'invalid_timestamp','invalid_action'} if simple else UNRELIABLE)]
            has_source=any(d['events'] or d['periods'] for d in result['days'])
            if not simple and not has_source and result['summary']['expected_seconds']!=0:bad.append('Geen betrouwbare registratiebron voor deze periode.')
            provisional[metric]=result['summary']['provisional']
            values[metric]=None if bad else duration(result['summary']['work_seconds'])+(' (voorlopig)' if provisional[metric] else '')
            if bad or (simple and warnings):issues[metric]=sorted(set(bad+warnings if simple else bad))
        month=details['month']; balance=month['summary']['balance_seconds']
        values['balance']=None if values['month'] is None or balance is None else duration(balance,True)+(' (voorlopig)' if month['summary']['provisional'] else '')
        if values['balance'] is None:issues['balance']=['Geen geldig rooster voor de volledige maand tot vandaag.'] if balance is None else issues.get('month',[])
        last=details['today']['days'][-1]
        values['status']=('Registratie met aandachtspunt' if simple else 'Afwijking — controleren') if last['anomalies'] else {'working':'Ingeklokt (voorlopig)','on_break':'In pauze (voorlopig)'}.get(last['open_status'],'Automatisch afgesloten' if any(n['code']=='automatic_stop' for n in last.get('notes',[])) else 'Afgesloten' if last['events'] or last['periods'] else 'Geen registratie')
        return {'values':values,'issues':issues,'simple_mode':simple,'provisional':provisional,'as_of':iso(now),
            'timezone':str(tz),'balance_period':{'start':str(today.replace(day=1)),'end':str(today)},'hr_revision':state['revision']}

    def preview(self,now=None,remote=True):
        config=self.config();rows=[]
        for employee in self.hr.employees():
            user=self.db.users.find_one({'_id':self._object_id(employee['id'])}) or {}
            if user.get('archived'):continue
            # Include staff with a roster, a binding, or actual registrations.
            if employee['role']!='user' and employee['id'] not in config['bindings'] and not self.hr.events(employee['id']):continue
            binding=config['bindings'].get(employee['id']);saved=self.db.loxone_sync_status.find_one({'_id':employee['id']}) or {}
            row={'employee':{k:employee[k] for k in ('id','username','name')},'binding':binding,
                'link_status':'Niet gekoppeld','last_success':saved.get('last_success'),
                'last_content_update':saved.get('last_content_update'),'last_error':saved.get('last_error'),
                'retry_at':saved.get('retry_at'),**self.totals(employee['id'],now)}
            identity=self.db.loxone_sync_meta.find_one({'_id':'identity:'+employee['id']}) or {}
            row['automatic_link']=config['auto_link']
            try:
                source=self.source_identity(user)
            except SyncError:
                source=None;row['last_error']=MESSAGES['identity_conflict']
            row['source_id']=source
            if identity.get('error_code'):row['last_error']=MESSAGES.get(identity['error_code'],MESSAGES['identity_conflict'])
            if config['auto_link'] and not binding:row['link_status']='Wordt automatisch gekoppeld via Loxone-ID' if source else 'Geen Loxone-ID ontvangen'
            row['desired']={f:row['values'].get(metric) or 'Niet beschikbaar' for f,metric in config['mapping'].items() if metric not in {'none','updated'}}
            if binding:
                row['link_status']='Automatisch gekoppeld via Loxone-ID' if binding.get('matched_by')=='loxone_id' else 'UUID gekoppeld (nog niet gecontroleerd)'
                if remote:
                    try:
                        actual=self.bridge.call('user',config['server'],uuid=binding['uuid'])
                        row['remote']=actual
                        row['link_status']='Hernoemd; UUID behouden' if actual['name']!=binding['name'] else 'Gekoppeld'
                        row['changes']={f:v for f,v in row['desired'].items() if actual['fields'].get(f)!=v}
                    except SyncError as exc:row['link_status']=MESSAGES[exc.code];row['last_error']=MESSAGES[exc.code]
            rows.append(row)
        return {'config':config,'rows':rows,'dry_run':True,'pending':self.db.loxone_sync_meta.find_one({'_id':'queue'}) or {},
                'run':self.db.loxone_sync_meta.find_one({'_id':'run'}) or {},
                'worker':self.db.loxone_sync_meta.find_one({'_id':'worker'}) or {},
                'transport':self.transport_status(config['server'])}

    @staticmethod
    def _object_id(uid):
        from bson import ObjectId
        return ObjectId(uid)

    def request_sync(self,actor):
        self.db.loxone_sync_meta.update_one({'_id':'queue'},{'$inc':{'sequence':1,'manual':0 if actor.startswith('system:') else 1},
            '$set':{'requested_at':clock(),'requested_by':actor}},upsert=True)
        return {'queued':True,'message':'Ingepland voor de eerstvolgende cronronde (normaal binnen één minuut).'}

    def run(self,now=None):
        started=instant(now or clock())
        self.db.loxone_sync_meta.update_one({'_id':'worker'},{'$set':{'started_at':started,'error_code':None}},upsert=True)
        try:
            result=self._run(now)
            self.db.loxone_sync_meta.update_one({'_id':'worker'},{'$set':{'finished_at':clock(),'result':result,'error_code':None}},upsert=True)
            return result
        except Exception as exc:
            code=exc.code if isinstance(exc,SyncError) else 'worker_failure'
            self.db.loxone_sync_meta.update_one({'_id':'worker'},{'$set':{'finished_at':clock(),'error_code':code}},upsert=True)
            raise

    def _run(self,now=None):
        now=instant(now or clock())
        with self.lock() as owner:
            config=self.config()
            if not config['server']:return {'disabled':True}
            config,identity_errors=self.automatic_links(config,owner)
            if not config['enabled']:return {'disabled':True,'identity_failed':len(identity_errors)}
            queue=self.db.loxone_sync_meta.find_one({'_id':'queue'}) or {}
            last=self.db.loxone_sync_meta.find_one({'_id':'run'}) or {}
            manual=queue.get('manual',0)>last.get('manual',0)
            due=not last.get('at') or (now-instant(last['at'])).total_seconds()>=config['interval']
            if not manual and not due:return {'waiting':True}
            success=writes=0;failed=len(identity_errors)
            for uid,binding in config['bindings'].items():
                if uid in identity_errors:continue
                saved=self.db.loxone_sync_status.find_one({'_id':uid}) or {}
                if saved.get('quarantined'):continue
                if not manual and saved.get('retry_at') and instant(saved['retry_at'])>now:continue
                try:
                    self.renew(owner)
                    user=self.db.users.find_one({'_id':self._object_id(uid)})
                    if not user or user.get('archived') or user.get('blocked'):continue
                    if binding['server']!=config['server']:raise SyncError('identity_changed')
                    if binding.get('matched_by')=='loxone_id':
                        current_source=self.source_identity(user)
                        if not current_source or self.identity_key(current_source)!=self.identity_key(binding['source_id']):raise SyncError('identity_conflict')
                    actual=self.bridge.call('user',config['server'],uuid=binding['uuid'])
                    totals=self.totals(uid,now)
                    values={f:totals['values'].get(metric) or 'Niet beschikbaar' for f,metric in config['mapping'].items() if metric not in {'none','updated'}}
                    patch={f:v for f,v in values.items() if actual['fields'].get(f)!=v}
                    content_at=saved.get('last_content_update')
                    attempt=saved.get('attempt')
                    if not patch and attempt and all(actual['fields'].get(f)==v for f,v in attempt['fields'].items()):
                        content_at=attempt['at']  # Lost response, subsequently confirmed by read-back.
                    if patch:
                        content_at=now
                        stamp=now.astimezone(ZoneInfo(totals['timezone'])).strftime('%d/%m/%Y %H:%M')
                        patch.update({f:stamp for f,m in config['mapping'].items() if m=='updated'})
                    # Never write a stale calculation after an intervening correction.
                    self.renew(owner)
                    if self.hr.state()['revision']!=totals['hr_revision']:raise SyncError('busy')
                    if patch:
                        if binding.get('matched_by')=='loxone_id':
                            fresh=self.db.users.find_one({'_id':self._object_id(uid)})
                            fresh_source=self.source_identity(fresh) if fresh else None
                            if not fresh_source or self.identity_key(fresh_source)!=self.identity_key(binding['source_id']):raise SyncError('identity_conflict')
                        self.db.loxone_sync_status.update_one({'_id':uid},{'$set':{'attempt':{'at':now,'fields':patch}}},upsert=True)
                        self.bridge.call('patch',config['server'],uuid=binding['uuid'],fields=patch)
                        writes+=1
                    self.db.loxone_sync_status.replace_one({'_id':uid},{'_id':uid,'last_success':now,
                        'last_content_update':content_at,'values':values,'last_error':None,'failures':0,
                        'link_name':actual['name'],'issues':totals['issues']},upsert=True)
                    success+=1
                except (SyncError,HRError) as exc:
                    code=exc.code if isinstance(exc,SyncError) else 'response'
                    failures=saved.get('failures',0)+1
                    self.db.loxone_sync_status.update_one({'_id':uid},{'$set':{'last_error':MESSAGES.get(code,MESSAGES['response']),
                        'error_code':code,'failures':failures,'quarantined':code=='verification',
                        'retry_at':now+timedelta(seconds=min(3600,60*2**min(failures-1,6)))}},upsert=True)
                    failed+=1
            self.db.loxone_sync_meta.replace_one({'_id':'run'},{'_id':'run','at':now,
                'sequence':queue.get('sequence',0),'manual':queue.get('manual',0),'success':success,'failed':failed,'writes':writes},upsert=True)
            return {'success':success,'failed':failed,'writes':writes}
