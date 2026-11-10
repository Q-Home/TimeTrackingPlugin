"""Provision synthetic identities through the real authenticated badge API."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import bcrypt
import mongomock
from bson import ObjectId
from flask_jwt_extended import create_access_token

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'bin/backend'))
os.environ.setdefault('JWT_SECRET_KEY','synthetic-provisioning-key-over-thirty-two-characters')
os.environ.setdefault('MONGO_URI','mongodb://localhost/synthetic_provisioning')
from app import create_app
from app.services.employee_provisioning import EmployeeProvisioning


class ProvisioningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.password=bcrypt.hashpw(b'synthetic-password',bcrypt.gensalt()).decode()
    def setUp(self):
        self.db=mongomock.MongoClient().synthetic_provisioning
        with patch('app.PyMongo',return_value=SimpleNamespace(db=self.db)):self.app=create_app()
        self.app.config.update(TESTING=True,INTERNAL_API_KEY='synthetic-ingress-key',JWT_SECRET_KEY='synthetic-signing-key-over-thirty-two-characters')
        self.client=self.app.test_client();self.hr=self.app.extensions['hr_service'];self.provision=self.app.extensions['employee_provisioning']
        self.ids={};self.tokens={}
        for role in ('user','hr','technical_admin'):
            uid=self.db.users.insert_one({'username':'synthetic.'+role,'email':role+'@example.invalid',
                'role':role,'password':self.password,'blocked':False}).inserted_id
            self.ids[role]=str(uid)
            with self.app.app_context():self.tokens[role]=create_access_token(identity='synthetic.'+role,additional_claims={'employee_id':str(uid),'role':'admin'})
    def headers(self,role):return {'Authorization':'Bearer '+self.tokens[role]}
    def badge(self,**extra):
        payload={'username':'synthetic.new','user_id':'SYNTHETIC-ID-001','action':'START','timestamp':'2026-11-10T08:00Z',**extra}
        return self.client.post('/api/v1/badges/',json=payload,headers={'X-Internal-API-Key':'synthetic-ingress-key'})
    def test_first_registration_creates_a_real_registration_only_employee(self):
        response=self.badge(first_name='Synthetic',last_name='New')
        self.assertEqual(response.status_code,201,response.json)
        employee=self.db.users.find_one({'user_id':'SYNTHETIC-ID-001'})
        self.assertEqual(employee['role'],'user');self.assertIsNone(employee['password'])
        self.assertEqual(response.json['data']['employee_id'],str(employee['_id']))
        self.assertEqual(self.db.badge_logs.find_one()['employee_id'],str(employee['_id']))
        self.assertEqual(self.hr.details(str(employee['_id']),datetime(2026,11,10).date(),datetime(2026,11,10).date())['employee']['name'],'Synthetic New')
    def test_repeated_userid_and_changed_source_name_keep_one_internal_id(self):
        first=self.badge().json['data']['employee_id']
        response=self.badge(username='renamed.synthetic',action='STOP',timestamp='2026-11-10T16:00Z')
        self.assertEqual(response.json['data']['employee_id'],first)
        self.assertEqual(self.db.users.count_documents({'user_id':'SYNTHETIC-ID-001'}),1)
        self.assertEqual(len(self.hr.events(first)),2)
    def test_numeric_and_alternative_userid_fields_work(self):
        for i,key in enumerate(('userid','userId','user_id')):
            response=self.client.post('/api/v1/badges/',json={key:100+i,'action':'SCAN'},headers={'X-Internal-API-Key':'synthetic-ingress-key'})
            self.assertEqual(response.status_code,201,response.json)
            self.assertIsNotNone(self.db.users.find_one({'user_id':str(100+i)}))
    def test_username_only_legacy_input_is_idempotent(self):
        first=self.badge(user_id='',username='legacy.synthetic').json['data']['employee_id']
        second=self.badge(user_id='',username='legacy.synthetic').json['data']['employee_id']
        self.assertEqual(first,second)
        third=self.badge(user_id='LATER-ID',username='legacy.synthetic').json['data']['employee_id']
        self.assertEqual(first,third)
    def test_short_source_name_gets_safe_internal_name_and_can_gain_userid(self):
        first=self.badge(user_id='',username='Al').json['data']['employee_id']
        second=self.badge(user_id='AL-ID',username='Al').json['data']['employee_id']
        self.assertEqual(first,second);self.assertTrue(self.db.users.find_one({'_id':ObjectId(first)})['username'].startswith('loxone-'))
    def test_multiple_accounts_need_no_real_email_and_do_not_collide(self):
        for i in range(5):self.assertEqual(self.badge(user_id=str(i),username='synthetic.'+str(i)).status_code,201)
        self.assertEqual(self.db.users.count_documents({'provisioned_by':'loxone'}),5)
        self.assertEqual(len(set(u['email'] for u in self.db.users.find({'provisioned_by':'loxone'}))),5)
    def test_legacy_numeric_userid_matches_without_a_username(self):
        self.db.users.update_one({'_id':ObjectId(self.ids['user'])},{'$set':{'user_id':123}})
        response=self.badge(user_id=123,username='')
        self.assertEqual(response.json['data']['employee_id'],self.ids['user'])
    def test_payload_cannot_set_password_role_or_privileged_state(self):
        self.badge(role='admin',password='must-not-be-used',blocked=False,employee_id=self.ids['technical_admin'])
        employee=self.db.users.find_one({'user_id':'SYNTHETIC-ID-001'})
        self.assertEqual(employee['role'],'user');self.assertIsNone(employee['password'])
        self.assertNotEqual(str(employee['_id']),self.ids['technical_admin'])
    def test_public_web_request_cannot_provision_an_employee(self):
        for headers in ({},self.headers('user'),self.headers('hr')):
            response=self.client.post('/api/v1/badges/',json={'username':'must.not.exist','user_id':'FORGED','action':'START'},headers=headers)
            self.assertIn(response.status_code,(401,403,409))
        self.assertIsNone(self.db.users.find_one({'user_id':'FORGED'}))
    def test_invalid_registration_or_conflicting_ids_creates_no_account(self):
        for extra in ({'action':'INVALID'},{'timestamp':'invalid'},{'userid':'OTHER'},{'user_id':{'bad':'id'}}):
            self.assertEqual(self.badge(**extra).status_code,400)
        self.assertIsNone(self.db.users.find_one({'user_id':'SYNTHETIC-ID-001'}))
    def test_manual_employee_is_linked_without_changing_credentials_or_role(self):
        before=self.db.users.find_one({'_id':ObjectId(self.ids['user'])})
        response=self.badge(username='synthetic.user')
        self.assertEqual(response.json['data']['employee_id'],self.ids['user'])
        after=self.db.users.find_one({'_id':before['_id']})
        for key in ('password','role','email','blocked'):self.assertEqual(before[key],after[key])
    def test_privileged_name_is_not_claimed_by_a_new_userid(self):
        response=self.badge(username='synthetic.technical_admin')
        self.assertNotEqual(response.json['data']['employee_id'],self.ids['technical_admin'])
        employee=self.db.users.find_one({'user_id':'SYNTHETIC-ID-001'})
        self.assertEqual(employee['role'],'user')
    def test_reused_name_with_a_new_id_does_not_merge_employees(self):
        first=self.badge().json['data']['employee_id']
        second=self.badge(user_id='DIFFERENT-ID').json['data']['employee_id']
        self.assertNotEqual(first,second)
        self.assertEqual(self.db.badge_logs.count_documents({'employee_id':first}),1)
    def test_archived_identity_is_not_reactivated_or_renamed_into_another(self):
        first=self.badge().json['data']['employee_id']
        self.db.users.update_one({'_id':ObjectId(first)},{'$set':{'archived':True,'blocked':True}})
        self.assertEqual(self.badge().json['data']['employee_id'],first)
        new=self.badge(user_id='A-NEW-PERSON').json['data']['employee_id']
        self.assertNotEqual(first,new);self.assertTrue(self.db.users.find_one({'_id':ObjectId(first)})['blocked'])
    def test_duplicate_existing_ids_keep_registration_unresolved(self):
        self.db.users.update_one({'_id':ObjectId(self.ids['user'])},{'$set':{'user_id':'AMBIGUOUS'}})
        self.db.users.update_one({'_id':ObjectId(self.ids['hr'])},{'$set':{'user_id':'AMBIGUOUS'}})
        response=self.badge(user_id='AMBIGUOUS')
        self.assertEqual(response.status_code,201,response.json)
        self.assertEqual(response.json['data']['provisioning_status'],'identity_conflict')
        record=self.db.badge_logs.find_one();self.assertIsNone(record['employee_id'])
        self.assertTrue(self.hr.resolve(record).startswith('unresolved:'))
        state=self.hr.state()
        self.hr.setting('identity',{'revision':state['revision'],'identity_key':'external:AMBIGUOUS','employee_id':self.ids['user'],'reason':'Synthetic reviewed identity'},'synthetic.hr','reviewed-identity-001')
        self.assertEqual(self.hr.resolve(record),self.ids['user'])
    def test_approval_guard_blocks_silent_identity_link_but_preserves_badge(self):
        self.db.hr_state.replace_one({'_id':'hr'},{**self.hr.state(),'revision':1,'approvals':[{'id':'approval','employee_id':self.ids['user'],
            'start':'2026-01-01','end':'2026-01-02','status':'closed'}]})
        response=self.badge(username='synthetic.user')
        self.assertEqual(response.status_code,201,response.json)
        self.assertEqual(response.json['data']['provisioning_status'],'identity_conflict')
        self.assertEqual(self.db.badge_logs.count_documents({}),1)
    def test_parallel_retries_provision_exactly_one_identity(self):
        data=EmployeeProvisioning.normalize({'username':'parallel.synthetic','user_id':'PARALLEL'})
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(lambda _:self.provision.ensure(data),range(8)))
        self.assertEqual(len({str(r['user']['_id']) for r in results}),1)
        self.assertEqual(self.db.users.count_documents({'user_id':'PARALLEL'}),1)
    def test_userid_only_registration_has_correct_account_scan_count(self):
        uid=self.badge(username='').json['data']['employee_id']
        response=self.client.get('/api/v1/users/',headers=self.headers('technical_admin'))
        employee=next(u for u in response.json['data']['users'] if u.get('employee_id')==uid)
        self.assertEqual(employee['total_scans'],1);self.assertFalse(employee['web_access'])
    def test_legacy_external_identity_does_not_merge_into_a_different_same_named_person(self):
        self.db.users.update_one({'_id':ObjectId(self.ids['user'])},{'$set':{'user_id':'ORIGINAL'}})
        record={'username':'synthetic.user','user_id':'DIFFERENT'}
        self.assertTrue(self.hr.resolve(record).startswith('unresolved:'))
        self.assertEqual(self.hr.identity_key(record),'external:DIFFERENT')
    def test_source_rename_does_not_add_a_duplicate_pseudo_account_in_the_list(self):
        self.badge();self.badge(username='changed.source.name')
        response=self.client.get('/api/v1/users/',headers=self.headers('technical_admin'))
        rows=response.json['data']['users']
        self.assertFalse(any(row['username']=='changed.source.name' for row in rows))
        self.assertEqual(next(row for row in rows if row['username']=='synthetic.new')['total_scans'],2)
    def test_existing_provisioning_metadata_cannot_be_erased_in_profile_form(self):
        uid=self.badge().json['data']['employee_id'];employee=self.db.users.find_one({'_id':ObjectId(uid)})
        response=self.client.put('/api/v1/users/'+uid,headers=self.headers('technical_admin'),json={
            'username':employee['username'],'email':employee['email'],'role':'user','extra_fields':{'provisioning_key':'forged'}})
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(self.db.users.find_one({'_id':ObjectId(uid)})['provisioning_key'],employee['provisioning_key'])
        response=self.client.put('/api/v1/users/'+uid,headers=self.headers('technical_admin'),json={
            'username':employee['username'],'email':'real-address@example.invalid','role':'user','extra_fields':{}})
        self.assertEqual(response.status_code,200,response.json)
        self.assertFalse(self.db.users.find_one({'_id':ObjectId(uid)})['email_is_placeholder'])
    def test_existing_users_events_branding_and_config_survive_restart(self):
        self.badge();self.db.app_settings.insert_one({'key':'branding','value':{'brand_name':'Synthetic company'}})
        before=list(self.db.users.find({}));events=list(self.db.badge_logs.find({}))
        with patch('app.PyMongo',return_value=SimpleNamespace(db=self.db)):create_app()
        self.assertEqual(before,list(self.db.users.find({})));self.assertEqual(events,list(self.db.badge_logs.find({})))
        self.assertEqual(self.db.app_settings.find_one({'key':'branding'})['value']['brand_name'],'Synthetic company')
    def test_registration_only_employees_cannot_login_even_with_a_password(self):
        self.badge()
        for name in ('synthetic.new','synthetic.user'):
            response=self.client.post('/api/v1/login',json={'username':name,'password':'synthetic-password'})
            self.assertEqual(response.status_code,403,response.json)
            self.assertNotIn('access_token',str(response.json))
    def test_old_employee_jwt_and_forged_admin_claim_are_rejected(self):
        for path in ('/api/v1/hr/me','/api/v1/hr/overview','/api/v1/users/synthetic.user','/api/v1/badges/'):
            self.assertEqual(self.client.get(path,headers=self.headers('user')).status_code,403,path)
    def test_hr_and_technical_login_remain_available_with_exact_password(self):
        for role in ('hr','technical_admin'):
            response=self.client.post('/api/v1/login',json={'username':'synthetic.'+role,'password':'synthetic-password'})
            self.assertEqual(response.status_code,200,response.json)
        self.db.users.update_one({'_id':ObjectId(self.ids['hr'])},{'$set':{'password':bcrypt.hashpw(b' spaced password ',bcrypt.gensalt()).decode()}})
        self.assertEqual(self.client.post('/api/v1/login',json={'username':'synthetic.hr','password':' spaced password '}).status_code,200)
    def test_missing_hash_and_malformed_login_return_a_controlled_error(self):
        self.db.users.update_one({'_id':ObjectId(self.ids['hr'])},{'$set':{'password':None}})
        self.assertEqual(self.client.post('/api/v1/login',json={'username':'synthetic.hr','password':'some-value'}).status_code,401)
        for payload in (['bad'],{'username':123,'password':{}},{}):
            self.assertEqual(self.client.post('/api/v1/login',json=payload).status_code,400)


if __name__=='__main__':unittest.main()
