"""Simple defaults and ID-driven delivery, using synthetic identities only."""
from copy import deepcopy
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
import os,sys,unittest
from unittest.mock import patch
import mongomock
from bson import ObjectId
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bin/backend'))
os.environ.setdefault('MONGO_URI','mongodb://localhost/synthetic_simple_time')
os.environ.setdefault('JWT_SECRET_KEY','synthetic-simple-key-more-than-thirty-two-bytes')
from app import create_app
from app.hr.engine import policy
from app.hr.service import HRService,HRError,identifier
from app.loxone_sync.service import SyncService,FIELDS
from app.loxone_sync.bridge import SyncError
import test_loxone_sync as legacy

UUID=legacy.UUID;SERVER=legacy.SERVER
NOW=datetime(2026,11,19,15,tzinfo=timezone.utc)

class IdentityBridge(legacy.FakeBridge):
    def __init__(self):
        super().__init__();self.ids={UUID:UUID,'1234':UUID};self.resolutions=[]
    def call(self,operation,server=None,**data):
        if operation=='resolve':
            self.resolutions.append(data['userid'])
            if self.error:raise SyncError(self.error)
            target=self.ids.get(data['userid'])
            user=next((u for u in self.users if u['uuid']==target),None)
            if not user:raise SyncError('identity_not_found')
            return {**user,'source_id':data['userid']}
        return super().call(operation,server,**data)

class SimpleTimeTests(unittest.TestCase):
    def setUp(self):
        self.db=mongomock.MongoClient().synthetic_simple
        self.hr=HRService(self.db);self.hr.initialize_defaults();self.hr.initialize_simple_mode()
        self.db.hr_state.update_one({'_id':'hr'},{'$set':{'default_regime_from':'2026-11-01'}})
        self.uid=str(self.db.users.insert_one({'username':'synthetic.employee','role':'user','user_id':UUID}).inserted_id)
        self.bridge=IdentityBridge();self.sync=SyncService(self.db,self.hr,self.bridge)
    def events(self,pairs,on='2026-11-19',**extra):
        for action,time in pairs:
            self.db.badge_logs.insert_one({'employee_id':self.uid,'username':'synthetic.employee','user_id':UUID,
                'action':action,'timestamp':on+'T'+time+'Z',**extra})
    def configure(self,enabled=True):
        self.sync.save({'revision':self.sync.config()['revision'],'server':SERVER,'enabled':enabled,'interval':600,
            'mapping':{f:'today' if i==0 else 'none' for i,f in enumerate(FIELDS)},'owned_fields':['customField1'],
            'reason':'Synthetic configuration'},'synthetic.admin')
    def run_sync(self):
        with patch('app.loxone_sync.service.clock',return_value=NOW):return self.sync.run(NOW)
    def test_default_migration_is_persistent_and_audited_once(self):
        state=self.hr.state();self.hr.initialize_simple_mode()
        self.assertEqual(state,self.hr.state());self.assertTrue(state['simple_mode'])
        self.assertEqual(sum(a['kind']=='workflow' for a in state['audit']),1)
        self.assertFalse(policy(state,date(2026,11,19))['approval_required'])
    def test_automatic_stop_is_usable_without_manual_approval(self):
        self.events([('START','07:00')],on='2026-11-18')
        self.events([('STOP','15:00')],on='2026-11-18',raw_data={'auto_stop':True})
        detail=self.hr.details(self.uid,date(2026,11,18),date(2026,11,18),now=NOW)
        self.assertEqual(detail['approval_status'],'automatisch_goedgekeurd')
        self.assertEqual(detail['days'][0]['anomalies'],[])
        self.assertTrue(detail['days'][0]['notes']);self.assertEqual(self.hr.state()['approvals'],[])
        values=self.sync.totals(self.uid,NOW)['values']
        self.assertEqual(values['month'],'8u 00m');self.assertEqual(values['today'],'0u 00m')
        self.assertIsNotNone(values['balance'])
    def test_missing_registration_is_zero_and_does_not_block_other_days(self):
        values=self.sync.totals(self.uid,NOW)['values']
        self.assertEqual(values['today'],'0u 00m');self.assertEqual(values['month'],'0u 00m')
        self.assertEqual(values['status'],'Geen registratie')
    def test_live_hours_are_available_as_provisional(self):
        self.events([('START','08:00')])
        self.assertEqual(self.sync.totals(self.uid,NOW)['values']['today'],'7u 00m (voorlopig)')
    def test_corrupt_time_is_still_reported_not_fabricated(self):
        self.events([('START','08:00')]);self.db.badge_logs.insert_one({'employee_id':self.uid,'action':'STOP','timestamp':'not-a-date'})
        self.assertIsNone(self.sync.totals(self.uid,NOW)['values']['month'])
    def test_manual_mode_can_be_enabled_without_losing_events(self):
        self.events([('START','07:00'),('STOP','15:00')],raw_data={'auto_stop':True})
        before=list(self.db.badge_logs.find())
        self.hr.setting('workflow',{'revision':self.hr.state()['revision'],'simple_mode':False,'reason':'Synthetic manual workflow'},'synthetic.hr',identifier())
        self.hr.initialize_simple_mode();self.assertFalse(self.hr.state()['simple_mode'])
        self.assertIsNone(self.sync.totals(self.uid,NOW)['values']['today'])
        self.assertEqual(before,list(self.db.badge_logs.find()))
    def test_closed_snapshot_hash_and_edit_protection_are_preserved(self):
        self.events([('START','07:00'),('STOP','15:00')],on='2026-11-18')
        for action in ('approve','close'):
            self.hr.approval({'revision':self.hr.state()['revision'],'employee_id':self.uid,'start':'2026-11-18','end':'2026-11-18','action':action,'reason':'Synthetic closed period'},'synthetic.hr',identifier())
        self.db.hr_state.update_one({'_id':'hr'},{'$unset':{'simple_mode':''}})
        before=self.hr.calculation_hash(self.uid,date(2026,11,18),date(2026,11,18),self.hr.state())
        self.hr.initialize_simple_mode()
        self.assertEqual(before,self.hr.calculation_hash(self.uid,date(2026,11,18),date(2026,11,18),self.hr.state()))
        with self.assertRaises(HRError):self.hr.correct({'revision':self.hr.state()['revision'],'employee_id':self.uid,'new':{'action':'STOP','local_time':'2026-11-18T17:00'},'reason':'Synthetic blocked correction'},'synthetic.hr',identifier())
    def test_uuid_is_automatically_bound_and_written_without_link_button(self):
        self.events([('START','07:00'),('STOP','15:00')]);self.configure()
        result=self.run_sync();self.assertEqual(result['writes'],1)
        binding=self.sync.config()['bindings'][self.uid]
        self.assertEqual(binding['uuid'],UUID);self.assertEqual(binding['matched_by'],'loxone_id')
        self.assertEqual(self.bridge.fields['customField1'],'8')
        self.assertTrue(any(a['kind']=='automatic_binding' for a in self.db.loxone_sync_audit.find()))
    def test_renamed_account_still_matches_by_id(self):
        self.bridge.users[0]['name']='completely.different.name';self.configure();self.run_sync()
        self.assertEqual(self.sync.config()['bindings'][self.uid]['uuid'],UUID)
    def test_numeric_id_uses_server_resolution_and_is_rechecked(self):
        self.db.users.update_one({'_id':ObjectId(self.uid)},{'$set':{'user_id':'1234'}})
        self.configure();self.run_sync();self.assertEqual(self.bridge.resolutions,['1234'])
        with patch('app.loxone_sync.service.clock',return_value=NOW+timedelta(minutes=10)):self.sync.run(NOW+timedelta(minutes=10))
        self.assertEqual(self.bridge.resolutions,['1234','1234'])
    def test_id_reassignment_never_redirects_an_existing_binding(self):
        self.db.users.update_one({'_id':ObjectId(self.uid)},{'$set':{'user_id':'1234'}})
        self.configure();self.run_sync();self.bridge.calls=[]
        other='22345678-1234-1234-1234567890abcdef';self.bridge.users.append({'uuid':other,'name':'Other'});self.bridge.ids['1234']=other
        self.sync.request_sync('synthetic');result=self.run_sync()
        self.assertEqual(result['failed'],1);self.assertFalse(self.bridge.writes)
        self.assertEqual(self.sync.config()['bindings'][self.uid]['uuid'],UUID)
    def test_duplicate_local_ids_block_both_users(self):
        self.db.users.insert_one({'username':'second','role':'user','user_id':UUID})
        self.configure();result=self.run_sync()
        self.assertEqual(result['failed'],2);self.assertEqual(self.sync.config()['bindings'],{});self.assertFalse(self.bridge.writes)
    def test_missing_remote_id_never_falls_back_to_equal_name(self):
        self.db.users.update_one({'_id':ObjectId(self.uid)},{'$set':{'user_id':'UNKNOWN'}})
        self.configure();result=self.run_sync()
        self.assertEqual(result['failed'],1);self.assertFalse(self.bridge.writes);self.assertEqual(self.sync.config()['bindings'],{})
    def test_different_source_ids_resolving_to_one_person_block_both_writers(self):
        self.db.users.insert_one({'username':'second','role':'user','user_id':'1234'})
        self.configure();result=self.run_sync()
        self.assertEqual(result['failed'],2);self.assertFalse(self.bridge.writes)
    def test_missing_source_id_does_not_guess_by_name(self):
        self.db.users.update_one({'_id':ObjectId(self.uid)},{'$unset':{'user_id':''}})
        self.configure();self.run_sync()
        self.assertEqual(self.sync.config()['bindings'],{});self.assertFalse(self.bridge.resolutions)
        self.assertEqual(self.sync.preview(NOW,remote=False)['rows'][0]['link_status'],'Geen Loxone-ID ontvangen')
    def test_source_change_during_remote_read_prevents_a_stale_write(self):
        self.configure()
        original=self.bridge.call
        def changing(operation,server=None,**data):
            result=original(operation,server,**data)
            if operation=='user':self.db.users.update_one({'_id':ObjectId(self.uid)},{'$set':{'user_id':'CHANGED'}})
            return result
        self.bridge.call=changing
        self.assertEqual(self.run_sync()['failed'],1);self.assertFalse(self.bridge.writes)
    def test_legacy_id_is_recovered_from_events(self):
        self.db.users.update_one({'_id':ObjectId(self.uid)},{'$unset':{'user_id':''}})
        self.events([('START','07:00'),('STOP','15:00')]);self.configure();self.run_sync()
        self.assertEqual(self.sync.config()['bindings'][self.uid]['source_id'],UUID)
    def test_contradictory_event_id_is_not_auto_linked(self):
        self.events([('START','07:00')],user_id='OTHER-ID');self.configure();result=self.run_sync()
        self.assertEqual(result['failed'],1);self.assertFalse(self.bridge.writes)
        self.assertEqual(self.sync.config()['bindings'],{})
    def test_existing_manual_link_to_different_uuid_is_not_overwritten(self):
        other='22345678-1234-1234-1234567890abcdef'
        self.configure();self.db.loxone_sync_config.update_one({'_id':'settings'},{'$set':{'bindings':{self.uid:{'uuid':other,'name':'Other','server':SERVER}}}})
        self.assertEqual(self.run_sync()['failed'],1);self.assertEqual(self.sync.config()['bindings'][self.uid]['uuid'],other)
    def test_disabled_delivery_can_auto_link_but_never_write(self):
        self.configure(False);self.run_sync()
        self.assertIn(self.uid,self.sync.config()['bindings']);self.assertFalse(self.bridge.writes)
    def test_archived_and_blocked_accounts_are_not_auto_linked(self):
        for flag in ('archived','blocked'):
            self.db.users.update_one({'_id':ObjectId(self.uid)},{'$set':{flag:True}})
            self.configure();self.run_sync();self.assertFalse(self.bridge.resolutions)
            self.db.users.update_one({'_id':ObjectId(self.uid)},{'$unset':{flag:''}})
    def test_uuid_case_and_standard_hyphenation_have_one_identity_key(self):
        self.assertEqual(self.sync.identity_key(UUID),self.sync.identity_key('12345678-1234-1234-1234-567890ABCDEF'))
    def test_new_badge_creates_employee_and_syncs_without_approval_or_binding(self):
        db=mongomock.MongoClient().synthetic_ingress
        with patch('app.PyMongo',return_value=SimpleNamespace(db=db)):app=create_app()
        app.config.update(TESTING=True,INTERNAL_API_KEY='synthetic-ingress-key')
        client=app.test_client()
        for action,time in [('START','07:00'),('STOP','15:00')]:
            response=client.post('/api/v1/badges/',headers={'X-Internal-API-Key':'synthetic-ingress-key'},json={'user_id':UUID,'username':'new.synthetic','action':action,'timestamp':'2026-11-18T'+time+'Z'})
            self.assertEqual(response.status_code,201,response.json)
        uid=str(db.users.find_one({'user_id':UUID})['_id'])
        service=app.extensions['loxone_sync'];service.bridge=IdentityBridge()
        service.save({'revision':service.config()['revision'],'server':SERVER,'enabled':True,'interval':600,'mapping':{f:'month' if i==0 else 'none' for i,f in enumerate(FIELDS)},'owned_fields':['customField1'],'reason':'Synthetic delivery'},'synthetic.admin')
        with patch('app.loxone_sync.service.clock',return_value=NOW):result=service.run(NOW)
        self.assertEqual(result['writes'],1);self.assertEqual(service.bridge.fields['customField1'],'8')
        self.assertEqual(db.hr_state.find_one() ['approvals'],[])
        self.assertEqual(service.config()['bindings'][uid]['uuid'],UUID)

if __name__=='__main__':unittest.main()
