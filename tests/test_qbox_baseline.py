"""Regression coverage for the reconciled Qbox source, with no live services."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta

import mongomock

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'bin' / 'backend'
sys.path.insert(0, str(BACKEND))
os.environ['MONGO_URI'] = 'mongodb://127.0.0.1:27017/test_qbox_baseline'
os.environ['JWT_SECRET_KEY'] = 'unit-test-only-signing-key-not-for-deployment-000000'
os.environ['DEFAULT_ADMIN_PASSWORD'] = 'unit-test-only-password'
os.environ['INTERNAL_API_KEY'] = 'unit-test-only-internal-key'

from app import create_app
from flask_jwt_extended import create_access_token


class BaselineAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mongo = mongomock.MongoClient()
        cls.db = cls.mongo.test_qbox_baseline
        with patch('app.PyMongo', return_value=SimpleNamespace(db=cls.db)):
            cls.app = create_app()
        cls.app.config['TESTING'] = True
        with cls.app.app_context():
            cls.admin = create_access_token(identity='admin', additional_claims={'role':'admin'})
            cls.user = create_access_token(identity='example.user', additional_claims={'role':'user'})

    def setUp(self):
        self.db.badge_logs.delete_many({})
        self.db.app_settings.delete_many({})
        self.db.users.delete_many({'username':{'$ne':'admin'}})
        self.client = self.app.test_client()

    def headers(self, token=None):
        headers = {'X-TimeTracking-Public-Request':'1'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        return headers

    def test_missing_badge_code_remains_accepted_and_null(self):
        response = self.client.post('/api/v1/badges/', json={
            'username':'example.user', 'action':'START',
            'timestamp':'2026-11-09T08:00:00+01:00',
        }, headers=self.headers(self.user))
        self.assertEqual(response.status_code, 201, response.json)
        doc = self.db.badge_logs.find_one()
        self.assertIsNone(doc['badge_code'])
        self.assertEqual(doc['timestamp'], datetime(2026,11,9,7))

    def test_badge_code_is_resolved_from_existing_user(self):
        self.db.users.insert_one({'username':'example.user','badge_code':'SYNTHETIC-001'})
        response = self.client.post('/api/v1/badges/', json={
            'username':'example.user','action':'START',
        }, headers=self.headers(self.user))
        self.assertEqual(response.status_code, 201, response.json)
        self.assertEqual(self.db.badge_logs.find_one()['badge_code'],'SYNTHETIC-001')

    def test_explicit_badge_code_is_not_replaced_by_profile(self):
        self.db.users.insert_one({'username':'example.user','badge_code':'SYNTHETIC-001'})
        response = self.client.post('/api/v1/badges/', json={
            'username':'example.user','badge_code':'SYNTHETIC-002','action':'START',
        }, headers=self.headers(self.user))
        self.assertEqual(response.status_code, 201, response.json)
        self.assertEqual(self.db.badge_logs.find_one()['badge_code'],'SYNTHETIC-002')

    def test_invalid_create_action_is_rejected_without_insert(self):
        response = self.client.post('/api/v1/badges/', json={
            'username':'example.user','action':'NOT_AN_ACTION',
        }, headers=self.headers(self.user))
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.db.badge_logs.count_documents({}),0)

    def test_branding_is_readable_without_login_and_persists_admin_update(self):
        default = self.client.get('/api/v1/settings/branding')
        self.assertEqual(default.status_code,200)
        self.assertEqual(default.json['data']['brand_name'],'Q-Home')
        update = {'brand_name':'Synthetic test','accent_color':'#123456','logo_url':'images/test.png'}
        response = self.client.put('/api/v1/settings/branding',json=update,headers=self.headers(self.admin))
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(self.client.get('/api/v1/settings/branding').json['data'],update)
        self.assertEqual(self.db.app_settings.find_one({'key':'branding'})['value'],update)

    def test_normal_user_cannot_change_branding(self):
        response = self.client.put('/api/v1/settings/branding',json={'brand_name':'Forbidden'},headers=self.headers(self.user))
        self.assertEqual(response.status_code,403)
        self.assertEqual(self.db.app_settings.count_documents({}),0)

    def test_invalid_branding_is_rejected_without_saving(self):
        response = self.client.put('/api/v1/settings/branding',json={'accent_color':'red'},headers=self.headers(self.admin))
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.db.app_settings.count_documents({}),0)

    def test_timesheet_retains_event_origin_and_closed_work_interval(self):
        for action, hour in [('START',8),('STOP',16)]:
            self.db.badge_logs.insert_one({
                'username':'example.user','action':action,'timestamp':datetime(2026,11,9,hour),
                'badge_code':None,'device_id':'synthetic-reader','location':'Test room',
                'raw_data':{'synthetic':True},
            })
        response = self.client.get('/api/v1/timesheets/example.user?date=2026-11-09',headers=self.headers(self.user))
        self.assertEqual(response.status_code,200,response.json)
        data = response.json['data']
        self.assertEqual(data['work_seconds'],8*3600)
        for event in data['events']:
            self.assertEqual(event['device_id'],'synthetic-reader')
            self.assertEqual(event['location'],'Test room')
            self.assertEqual(event['raw_data'],{'synthetic':True})

    def test_normal_user_cannot_read_another_timesheet(self):
        response = self.client.get('/api/v1/timesheets/another.user?date=2026-11-09',headers=self.headers(self.user))
        self.assertEqual(response.status_code,403)


class AutoStopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('baseline_auto_stop',BACKEND/'scripts'/'auto_stop_missing_badges.py')
        cls.module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def setUp(self):
        self.collection=mongomock.MongoClient().test.badge_logs
        self.start=datetime(2026,11,8,7)
        self.start_id=self.collection.insert_one({
            'username':'example.user','action':'START','timestamp':self.start,'badge_code':None,
        }).inserted_id
        self.target=datetime(2026,11,8)
        self.run_time=datetime(2026,11,9,10,59)

    def test_dry_run_reports_stop_without_writing(self):
        with contextlib.redirect_stdout(io.StringIO()):
            count=self.module.run_day(self.collection,self.target,8,self.run_time,True)
        self.assertEqual(count,1)
        self.assertEqual(self.collection.count_documents({}),1)

    def test_stop_is_eight_elapsed_hours_after_start_and_is_idempotent(self):
        count=self.module.run_day(self.collection,self.target,8,self.run_time,False)
        self.assertEqual(count,1)
        stop=self.collection.find_one({'action':'STOP'})
        self.assertEqual(stop['timestamp'],self.start+timedelta(hours=8))
        self.assertTrue(stop['raw_data']['auto_stop'])
        self.assertEqual(stop['raw_data']['auto_stop_start_id'],str(self.start_id))
        self.assertEqual(self.module.run_day(self.collection,self.target,8,self.run_time,False),0)

    def test_future_stop_is_not_written(self):
        count=self.module.run_day(self.collection,self.target,8,self.start+timedelta(hours=4),False)
        self.assertEqual(count,0)
        self.assertEqual(self.collection.count_documents({}),1)

    def test_completed_session_is_not_corrected(self):
        self.collection.insert_one({'username':'example.user','action':'STOP','timestamp':self.start+timedelta(hours=7)})
        self.assertEqual(self.module.run_day(self.collection,self.target,8,self.run_time,False),0)


class TestHelperSafetyTests(unittest.TestCase):
    def test_mqtt_helper_has_no_password_fallback(self):
        helper=ROOT/'bin'/'MQTTService'/'send_test_badge.py'
        spec=importlib.util.spec_from_file_location('baseline_test_badge',helper)
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.dict(os.environ,{},clear=True),patch.object(sys,'argv',['send_test_badge.py']):
            self.assertEqual(module.build_parser().parse_args().password_auth,'')


if __name__=='__main__':
    unittest.main()
