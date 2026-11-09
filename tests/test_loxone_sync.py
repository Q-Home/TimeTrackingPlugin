"""Isolated delivery tests. No real Miniserver, broker or production identities."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import mongomock
from bson import ObjectId
from flask_jwt_extended import create_access_token

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bin/backend'))
from app import create_app
from app.hr.engine import DEFAULT_RULES
from app.hr.service import HRService,HRError
from app.loxone_sync.bridge import Bridge,SyncError,notify_change
from app.loxone_sync.service import SyncService,FIELDS

NOW=datetime(2026,11,9,15,tzinfo=timezone.utc)
UUID='12345678-1234-1234-1234567890abcdef'
SERVER={'slot':'1','serial':'AABBCCDDEEFF'}


class FakeBridge:
    def __init__(self):
        self.users=[{'uuid':UUID,'name':'synthetic.employee'}]
        self.fields={f:'Unmanaged '+f for f in FIELDS}
        self.calls=[];self.error=None
    def call(self,operation,server=None,**data):
        self.calls.append((operation,deepcopy(data)))
        if self.error:raise SyncError(self.error)
        if operation=='miniservers':return {'loxberry_version':'3.0.1','servers':[{'slot':'1','name':'Synthetic Miniserver'}]}
        if operation=='probe':return {'server':SERVER,'name':'Synthetic Miniserver','miniserver_version':'17.0.1.0','loxberry_version':'3.0.1','field_names':{f:f for f in FIELDS},'user_count':len(self.users)}
        if operation=='users':return deepcopy(self.users)
        user=next((u for u in self.users if u['uuid']==data['uuid']),None)
        if not user:raise SyncError('user_missing')
        if operation=='patch':self.fields.update(data['fields'])
        return {**user,'fields':deepcopy(self.fields)}
    @property
    def writes(self):return [c for c in self.calls if c[0]=='patch']


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.db=mongomock.MongoClient().synthetic_delivery
        self.uid=str(self.db.users.insert_one({'username':'synthetic.employee','role':'user'}).inserted_id)
        self.hr=HRService(self.db);self.bridge=FakeBridge();self.sync=SyncService(self.db,self.hr,self.bridge)
        state=self.hr.state();state['revision']=1
        state['schedules']=[{'id':'s1','name':'Synthetic 6h','days':[{'minutes':360} for _ in range(5)]+[{'minutes':0},{'minutes':0}]}]
        state['assignments']=[{'employee_id':self.uid,'schedule_id':'s1','effective_from':'2020-01-01'}]
        self.db.hr_state.insert_one(state)
        self.events([('START','2026-11-09T08:00Z'),('BREAK','2026-11-09T12:00Z'),('RETURN','2026-11-09T12:30Z'),('STOP','2026-11-09T14:30Z')])
    def events(self,items):
        for action,ts in items:self.db.badge_logs.insert_one({'employee_id':self.uid,'username':'synthetic.employee','action':action,'timestamp':ts})
    def configure(self,enabled=False,mapping=None,**extra):
        mapping=mapping or {f:('today' if i==0 else 'updated' if i==1 else 'none') for i,f in enumerate(FIELDS)}
        return self.sync.save({'revision':self.sync.config()['revision'],'enabled':enabled,'server':SERVER,
            'mapping':mapping,'interval':300,'reason':'Synthetic configuration','owned_fields':[f for f,v in mapping.items() if v!='none'],**extra},'synthetic.admin')
    def link(self,**extra):
        return self.sync.link({'revision':self.sync.config()['revision'],'employee_id':self.uid,'reason':'Synthetic link',**extra},'synthetic.admin')
    def run_sync(self,now=NOW):
        with patch('app.loxone_sync.service.clock',return_value=now):return self.sync.run(now)
    def test_default_is_off_and_does_not_contact_miniserver(self):
        self.assertEqual(self.run_sync(),{'disabled':True});self.assertEqual(self.bridge.calls,[])
    def test_exact_name_binding_and_manual_override(self):
        self.configure();self.link();self.assertEqual(self.sync.config()['bindings'][self.uid]['uuid'],UUID)
        self.bridge.users[0]['name']='different.name'
        self.link(loxone_username='different.name',replace=True)
        self.assertEqual(self.sync.config()['bindings'][self.uid]['name'],'different.name')
    def test_missing_or_ambiguous_names_require_manual_selection(self):
        self.configure();self.bridge.users[0]['name']='other'
        with self.assertRaises(HRError):self.link()
        self.link(uuid=UUID)
        self.assertEqual(self.sync.config()['bindings'][self.uid]['uuid'],UUID)
    def test_ambiguous_name_and_duplicate_uuid_are_rejected(self):
        self.configure();self.bridge.users.append({'uuid':'22345678-1234-1234-1234567890abcdef','name':'synthetic.employee'})
        with self.assertRaises(HRError):self.link()
        self.link(uuid=UUID)
        other=str(self.db.users.insert_one({'username':'other','role':'user'}).inserted_id)
        with self.assertRaises(HRError):self.link(employee_id=other,uuid=UUID)
    def test_deleted_user_is_not_replaced_by_same_name_account(self):
        self.configure(True);self.link()
        self.bridge.users[0]['uuid']='22345678-1234-1234-1234567890abcdef'
        self.assertEqual(self.run_sync()['failed'],1)
        self.assertEqual(self.sync.config()['bindings'][self.uid]['uuid'],UUID)
        self.assertFalse(self.bridge.writes)
    def test_renamed_user_keeps_uuid(self):
        self.configure(True);self.link();self.bridge.users[0]['name']='renamed'
        self.assertEqual(self.run_sync()['writes'],1)
        row=self.sync.preview(NOW)['rows'][0]
        self.assertEqual(row['link_status'],'Hernoemd; UUID behouden')
    def test_selected_fields_only_and_unchanged_values_skip_writes(self):
        self.configure(True);self.link();self.run_sync()
        patch_fields=self.bridge.writes[0][1]['fields']
        self.assertEqual(set(patch_fields),{'customField1','customField2'})
        self.assertEqual(patch_fields['customField1'],'6u 00m')
        self.assertEqual(self.bridge.fields['customField3'],'Unmanaged customField3')
        self.run_sync(NOW+timedelta(minutes=6));self.assertEqual(len(self.bridge.writes),1)
    def test_timestamp_alone_does_not_trigger_a_write(self):
        self.configure(True);self.link();self.run_sync();stamp=self.bridge.fields['customField2']
        self.run_sync(NOW+timedelta(minutes=10));self.assertEqual(stamp,self.bridge.fields['customField2']);self.assertEqual(len(self.bridge.writes),1)
    def test_dry_run_reads_values_but_never_writes(self):
        self.configure(True);self.link();preview=self.sync.preview(NOW)
        self.assertTrue(preview['dry_run']);self.assertTrue(preview['rows'][0]['changes']);self.assertFalse(self.bridge.writes)
    def test_activation_needs_explicit_ownership_and_content_metric(self):
        with self.assertRaises(HRError):self.configure(True,owned_fields=[])
        with self.assertRaises(HRError):self.configure(True,mapping={f:'updated' for f in FIELDS})
    def test_company_timezone_week_month_and_year_boundaries(self):
        self.db.badge_logs.delete_many({});self.events([('START','2026-12-31T22:00Z'),('STOP','2027-01-01T01:00Z')])
        values=self.sync.totals(self.uid,datetime(2027,1,1,10,tzinfo=timezone.utc))
        self.assertEqual(values['values']['today'],'2u 00m');self.assertEqual(values['values']['month'],'2u 00m')
        # New Monday and month discard prior-period registrations, rather than replaying old totals.
        self.assertIsNone(self.sync.totals(self.uid,datetime(2027,2,1,10,tzinfo=timezone.utc))['values']['week'])
        self.assertEqual(values['balance_period']['start'],'2027-01-01')
    def test_missing_schedule_does_not_invent_a_balance(self):
        self.db.hr_state.update_one({'_id':'hr'},{'$set':{'assignments':[]}})
        result=self.sync.totals(self.uid,NOW)
        self.assertEqual(result['values']['today'],'6u 00m');self.assertIsNone(result['values']['balance'])
    def test_live_pause_and_overnight_are_from_the_central_engine(self):
        self.db.badge_logs.delete_many({});self.events([('START','2026-11-09T08:00Z'),('BREAK','2026-11-09T12:00Z')])
        result=self.sync.totals(self.uid,NOW)
        self.assertEqual(result['values']['today'],'4u 00m (voorlopig)')
        self.assertEqual(result['values']['status'],'In pauze (voorlopig)')
    def test_correction_changes_delivery_without_changing_source(self):
        self.configure(True);self.link();self.run_sync()
        original=self.db.badge_logs.find_one({'action':'STOP'})
        self.hr.correct({'revision':1,'employee_id':self.uid,'target_id':str(original['_id']),
            'new':{'action':'STOP','timestamp':'2026-11-09T15:30Z'},'reason':'Synthetic correction'},'synthetic.hr','correction-id-001')
        self.run_sync(NOW+timedelta(hours=1,minutes=6))
        self.assertEqual(self.bridge.fields['customField1'],'7u 00m')
        self.assertEqual(self.db.badge_logs.find_one({'_id':original['_id']})['timestamp'],original['timestamp'])
    def test_unreliable_data_is_explicitly_unavailable(self):
        self.events([('START','2026-11-09T09:00Z')]);result=self.sync.totals(self.uid,NOW)
        self.assertIsNone(result['values']['today']);self.assertTrue(result['issues']['today'])
    def test_authentication_network_and_permission_errors_have_bounded_retry(self):
        self.configure(True);self.link()
        for code in ('authentication','permissions','network'):
            self.db.loxone_sync_status.delete_many({});self.db.loxone_sync_meta.delete_one({'_id':'run'})
            self.bridge.error=code;self.assertEqual(self.run_sync()['failed'],1)
            saved=self.db.loxone_sync_status.find_one({'_id':self.uid});self.assertEqual(saved['error_code'],code)
            self.assertEqual(saved['retry_at'].replace(tzinfo=timezone.utc),NOW+timedelta(minutes=1))
            self.assertNotIn('password',saved['last_error'].lower())
        self.bridge.error=None;self.run_sync(NOW+timedelta(minutes=6));self.assertEqual(len(self.bridge.writes),1)
    def test_changes_coalesce_and_another_writer_is_excluded(self):
        self.configure(True);self.link();self.run_sync()
        for _ in range(5):notify_change(self.db)
        with self.sync.lock():
            with self.assertRaises(SyncError):self.run_sync()
        result=self.run_sync(NOW+timedelta(minutes=6));self.assertEqual(result['writes'],0)
    def test_external_drift_is_repaired_only_in_managed_fields(self):
        self.configure(True);self.link();self.run_sync();self.bridge.fields['customField1']='wrong'
        self.run_sync(NOW+timedelta(minutes=6));self.assertEqual(self.bridge.fields['customField1'],'6u 00m')
    def test_bridge_failure_never_fails_timekeeping_notification(self):
        with patch.object(self.db.loxone_sync_meta,'update_one',side_effect=RuntimeError('synthetic-private-string')):
            self.hr.commit(self.hr.state(),deepcopy(self.hr.state()))
        self.assertEqual(self.hr.state()['revision'],2)
    def test_recovery_sends_current_values_not_queued_old_payload(self):
        self.configure(True);self.link();self.bridge.error='network';self.run_sync()
        self.bridge.error=None
        self.db.badge_logs.update_one({'action':'STOP'},{'$set':{'timestamp':'2026-11-09T15:00Z'}})
        self.run_sync(NOW+timedelta(minutes=6))
        self.assertEqual(self.bridge.fields['customField1'],'6u 30m')
    def test_unsafe_readback_is_quarantined_until_explicit_relink(self):
        self.configure(True);self.link();self.bridge.error='verification';self.run_sync()
        self.bridge.error=None;self.run_sync(NOW+timedelta(minutes=6))
        self.assertFalse(self.bridge.writes)
        self.link(replace=True,uuid=UUID)
        self.run_sync(NOW+timedelta(minutes=7));self.assertEqual(len(self.bridge.writes),1)
    def test_no_connection_exception_details_escape(self):
        with patch('socket.socket',side_effect=OSError('password=synthetic-secret')):
            with self.assertRaises(SyncError) as error:Bridge().call('users',SERVER)
        self.assertEqual(str(error.exception),'bridge_unavailable')


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.db=mongomock.MongoClient().sync_roles
        with patch('app.PyMongo',return_value=SimpleNamespace(db=self.db)):self.app=create_app()
        self.app.config.update(TESTING=True,JWT_SECRET_KEY='synthetic-signing-key-longer-than-thirty-two')
        self.client=self.app.test_client();self.tokens={}
        for role in ('user','hr','technical_admin','admin'):
            uid=self.db.users.insert_one({'username':'synthetic.'+role,'role':role,'email':role+'@example.invalid'}).inserted_id
            with self.app.app_context():self.tokens[role]=create_access_token(identity='synthetic.'+role,additional_claims={'employee_id':str(uid)})
        self.app.extensions['loxone_sync'].bridge=FakeBridge()
    def test_every_endpoint_enforces_technical_authorization(self):
        endpoints=[('get','config'),('get','miniservers'),('get','users'),('get','diagnostics'),
            ('post','config'),('post','test'),('post','links'),('post','preview'),('post','run')]
        for role in ('user','hr'):
            for method,path in endpoints:
                response=getattr(self.client,method)('/api/v1/loxone-sync/'+path,headers={'Authorization':'Bearer '+self.tokens[role]},json={})
                self.assertEqual(response.status_code,403,(role,path,response.json))
        for role in ('technical_admin','admin'):
            self.assertEqual(self.client.get('/api/v1/loxone-sync/config',headers={'Authorization':'Bearer '+self.tokens[role]}).status_code,200)
    def test_anonymous_has_no_access_and_no_credentials_in_inventory(self):
        self.assertEqual(self.client.get('/api/v1/loxone-sync/miniservers').status_code,401)
        data=self.client.get('/api/v1/loxone-sync/miniservers',headers={'Authorization':'Bearer '+self.tokens['admin']}).json
        self.assertNotIn('password',json.dumps(data).lower())
    def test_manual_action_only_enqueues_no_inline_worker(self):
        service=self.app.extensions['loxone_sync']
        response=self.client.post('/api/v1/loxone-sync/run',headers={'Authorization':'Bearer '+self.tokens['admin']})
        self.assertEqual(response.status_code,202);self.assertFalse(service.bridge.calls)


if __name__=='__main__':unittest.main()
