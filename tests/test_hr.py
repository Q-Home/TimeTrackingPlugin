"""Synthetic HR regression cases; no production database, MQTT or correction job."""
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from datetime import date, datetime, timedelta, timezone

import mongomock
from bson import ObjectId
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bin/backend'))
os.environ.setdefault('MONGO_URI','mongodb://localhost:27017/synthetic_hr')
os.environ.setdefault('JWT_SECRET_KEY','synthetic-test-signing-key-with-at-least-32-bytes')
from app import create_app
from app.hr.engine import calculate, DEFAULT_RULES
from app.hr.service import HRService, HRError, identifier
from flask_jwt_extended import create_access_token

NOW=datetime(2026,11,11,15,tzinfo=timezone.utc)


def event(action,ts,**extra):
    return {'_id':ObjectId(),'action':action,'timestamp':ts,'username':'synthetic.user',**extra}


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.employee={'id':'e1','department':'Operations'}
        self.state={'schedules':[{'id':'s1','days':[{'minutes':360} for _ in range(5)]+[{'minutes':0},{'minutes':0}]}],
            'assignments':[{'employee_id':'e1','schedule_id':'s1','effective_from':'2020-01-01'}],
            'calendar':[],'policies':[]}
    def calc(self,events,start='2026-11-09',end=None,**kw):
        return calculate(events,self.state,self.employee,date.fromisoformat(start),date.fromisoformat(end or start),now=kw.pop('now',NOW),**kw)
    def test_normal_workday_with_multiple_breaks(self):
        events=[event(a,'2026-11-09T'+t+'+01:00') for a,t in [('START','08:00'),('BREAK','10:00'),('RETURN','10:15'),('BREAK','12:00'),('RETURN','12:45'),('STOP','17:00')]]
        result=self.calc(events)['days'][0]
        self.assertEqual(result['work_seconds'],8*3600);self.assertEqual(result['break_seconds'],3600)
        self.assertEqual(len(result['periods']),5)
    def test_overnight_is_split_after_utc_duration_calculation(self):
        result=self.calc([event('START','2026-11-09T22:00+01:00'),event('STOP','2026-11-10T06:00+01:00')],end='2026-11-10')
        self.assertEqual([d['work_seconds'] for d in result['days']],[7200,21600])
    def test_spring_and_autumn_transitions_use_elapsed_duration(self):
        for on,start,stop,hours in [('2026-03-29','00:00+01:00','04:00+02:00',3),('2026-10-25','00:00+02:00','04:00+01:00',5)]:
            result=self.calc([event('START',on+'T'+start),event('STOP',on+'T'+stop)],start=on)
            self.assertEqual(result['summary']['work_seconds'],hours*3600)
    def test_part_time_and_assignment_history(self):
        self.state['schedules'].append({'id':'s2','days':[{'minutes':240} for _ in range(7)]})
        self.state['assignments'].append({'employee_id':'e1','schedule_id':'s2','effective_from':'2026-11-10'})
        result=self.calc([],end='2026-11-10')
        self.assertEqual([d['expected_seconds'] for d in result['days']],[21600,14400])
    def test_weekend_holiday_and_individual_absence(self):
        self.state['calendar']=[{'id':'c1','start':'2026-11-09','end':'2026-11-09','effect':'zero'},
            {'id':'c2','employee_id':'e1','start':'2026-11-10','end':'2026-11-10','effect':'hours','minutes':120}]
        result=self.calc([],start='2026-11-07',end='2026-11-10')
        self.assertEqual([d['expected_seconds'] for d in result['days']],[0,0,0,7200])
    def test_future_days_do_not_produce_a_deficit(self):
        result=self.calc([],end='2026-11-13')
        self.assertEqual(result['summary']['expected_seconds'],18*3600)
        self.assertEqual(result['summary']['full_expected_seconds'],30*3600)
        self.assertEqual(result['days'][-1]['balance_seconds'],0)
        self.assertFalse(result['days'][-1]['anomalies'])
    def test_no_schedule_has_no_fictitious_deficit(self):
        self.state['assignments']=[];result=self.calc([])
        self.assertIsNone(result['summary']['expected_seconds']);self.assertIsNone(result['summary']['balance_seconds'])
        self.assertFalse(result['days'][0]['anomalies'])
    def test_duplicate_start_missing_stop_and_live_time(self):
        result=self.calc([event('START','2026-11-11T08:00Z'),event('START','2026-11-11T09:00Z')],start='2026-11-11')['days'][0]
        self.assertEqual(result['work_seconds'],7*3600);self.assertTrue(result['provisional'])
        self.assertIn('duplicate_start',[a['code'] for a in result['anomalies']])
        old=self.calc([event('START','2026-11-09T08:00Z')])['days'][0]
        self.assertIn('missing_stop',[a['code'] for a in old['anomalies']])
    def test_actual_break_is_not_deducted_twice(self):
        self.state['policies']=[{'effective_from':'2020-01-01','rules':{**DEFAULT_RULES,'break_mode':'automatic','automatic_break_minutes':30}}]
        events=[event(a,'2026-11-09T'+t+'Z') for a,t in [('START','08:00'),('BREAK','12:00'),('RETURN','12:30'),('STOP','16:30')]]
        result=self.calc(events)['days'][0]
        self.assertEqual(result['work_seconds'],8*3600);self.assertEqual(result['automatic_break_seconds'],0)
        result=self.calc([event('START','2026-11-09T08:00Z'),event('STOP','2026-11-09T16:00Z')])['days'][0]
        self.assertEqual(result['work_seconds'],7.5*3600);self.assertEqual(result['automatic_break_seconds'],1800)
    def test_long_open_threshold_includes_time_before_a_break(self):
        events=[event(a,'2026-11-11T'+t+'Z') for a,t in [('START','00:00'),('BREAK','12:00'),('RETURN','12:30')]]
        result=self.calc(events,start='2026-11-11',now=datetime(2026,11,11,18,tzinfo=timezone.utc))['days'][0]
        self.assertIn('long_open',[a['code'] for a in result['anomalies']])
    def test_automatic_stop_is_a_visible_anomaly(self):
        result=self.calc([event('START','2026-11-09T08:00Z'),event('STOP','2026-11-09T16:00Z',raw_data={'auto_stop':True})])['days'][0]
        self.assertIn('automatic_stop',[a['code'] for a in result['anomalies']])
        self.assertEqual(result['events'][1]['source'],'automatic')


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.db=mongomock.MongoClient().synthetic
        self.uid=str(self.db.users.insert_one({'username':'synthetic.user','role':'user','first_name':'Synthetic','last_name':'Person'}).inserted_id)
        self.hr=HRService(self.db)
        self.start=self.db.badge_logs.insert_one(event('START','2020-01-06T08:00Z',employee_id=self.uid)).inserted_id
        self.stop=self.db.badge_logs.insert_one(event('STOP','2020-01-06T14:00Z',employee_id=self.uid)).inserted_id
        schedule=self.setting('schedule',schedule={'name':'Synthetic part-time','days':[{'minutes':360} for _ in range(5)]+[{'minutes':0},{'minutes':0}]})['value']
        self.setting('assignment',employee_id=self.uid,schedule_id=schedule['id'],effective_from='2020-01-01')
    def data(self,**values):return {'revision':self.hr.state()['revision'],'reason':'Synthetic test reason',**values}
    def setting(self,setting_kind,**values):return self.hr.setting(setting_kind,self.data(**values),'synthetic.hr',identifier())
    def approve(self,action='approve',**extra):
        return self.hr.approval(self.data(employee_id=self.uid,start='2020-01-06',end='2020-01-06',action=action,**extra),'synthetic.hr',identifier())
    def correction(self,**values):return self.hr.correct(self.data(employee_id=self.uid,target_id=str(self.stop),new={'action':'STOP','timestamp':'2020-01-06T15:00Z'},**values),'synthetic.hr',identifier())
    def test_correction_preserves_raw_and_is_atomic_with_audit(self):
        before=self.db.badge_logs.find_one({'_id':self.stop})
        result=self.correction()
        self.assertEqual(before,self.db.badge_logs.find_one({'_id':self.stop}))
        self.assertEqual(self.hr.details(self.uid,date(2020,1,6),date(2020,1,6))['summary']['work_seconds'],7*3600)
        audit=self.hr.state()['audit'][-1]
        self.assertEqual(audit['reference'],str(self.stop));self.assertEqual(audit['actor'],'synthetic.hr')
        self.assertEqual(audit['new']['timestamp'],'2020-01-06T15:00:00Z');self.assertTrue(result['correction']['old'])
    def test_duplicate_operation_replays_and_conflicting_revision_is_rejected(self):
        data=self.data(employee_id=self.uid,target_id=str(self.stop),new={'action':'STOP','timestamp':'2020-01-06T15:00Z'})
        key=identifier();one=self.hr.correct(data,'synthetic.hr',key);two=self.hr.correct(data,'synthetic.hr',key)
        self.assertTrue(two['replayed']);self.assertEqual(len(self.hr.state()['corrections']),1)
        with self.assertRaises(HRError):self.hr.correct(data,'synthetic.hr',identifier())
    def test_closed_period_rejects_corrections_until_audited_reopening(self):
        self.approve();self.approve('close')
        with self.assertRaises(HRError):self.correction()
        self.approve('reopen');self.correction()
        self.assertTrue(any(a['kind']=='period_reopen' for a in self.hr.state()['audit']))
    def test_approved_hours_require_explicit_invalidation(self):
        self.approve()
        with self.assertRaises(HRError):self.correction()
        self.correction(invalidate_approval=True)
        self.assertEqual(self.hr.state()['approvals'][0]['status'],'invalidated')
    def test_roster_and_rule_changes_cannot_silently_change_approval(self):
        self.approve()
        with self.assertRaises(HRError):self.setting('policy',effective_from='2020-01-01',rules={**DEFAULT_RULES,'break_mode':'automatic','automatic_break_minutes':30})
        with self.assertRaises(HRError):self.setting('calendar',start='2020-01-06',end='2020-01-06',kind='holiday',effect='zero')
    def test_new_event_cannot_race_with_period_closing(self):
        incoming=event('SCAN','2020-01-06T09:00Z',employee_id=self.uid)
        token=self.hr.reserve_event(incoming)
        with self.assertRaises(HRError):self.approve()
        self.db.badge_logs.insert_one(incoming);self.hr.finish_event(token)
        self.approve();self.approve('close')
        with self.assertRaises(HRError):self.hr.reserve_event(event('STOP','2020-01-06T17:00Z',employee_id=self.uid))
    def test_corrupt_external_write_is_not_shown_as_valid_approval(self):
        self.approve();self.db.badge_logs.update_one({'_id':self.stop},{'$set':{'timestamp':'2020-01-06T17:00Z'}})
        result=self.hr.details(self.uid,date(2020,1,6),date(2020,1,6))
        self.assertEqual(result['approval_status'],'bron_gewijzigd')
        with self.assertRaises(HRError):self.approve('close')
    def test_dst_manual_correction_requires_valid_local_time_and_fold(self):
        for local in ('2026-03-29T02:30','2026-10-25T02:30'):
            data=self.data(employee_id=self.uid,new={'action':'START','local_time':local})
            with self.assertRaises(HRError):self.hr.correct(data,'synthetic.hr',identifier())
        data=self.data(employee_id=self.uid,new={'action':'START','local_time':'2026-10-25T02:30','fold':1})
        result=self.hr.correct(data,'synthetic.hr',identifier())
        self.assertEqual(result['correction']['new']['timestamp'],'2026-10-25T01:30:00Z')
    def test_identity_migration_is_explicit_and_idempotent(self):
        spec=importlib.util.spec_from_file_location('hr_migrate',ROOT/'bin/backend/scripts/hr_migrate.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.db.badge_logs.update_many({}, {'$unset':{'employee_id':''}})
        self.db.badge_logs.insert_one(event('SCAN','2020-01-06T10:00Z',username='unresolved.synthetic'))
        preview=module.migrate(self.hr)
        self.assertTrue(preview['unresolved']);self.assertEqual(len(self.hr.state()['identity_links']),0)
        module.migrate(self.hr,True);module.migrate(self.hr,True)
        self.db.users.update_one({'_id':ObjectId(self.uid)},{'$set':{'username':'renamed.synthetic'}})
        self.assertEqual(len(self.hr.events(self.uid)),2)
        self.assertEqual(self.hr.events(self.uid)[0]['action'],'START')
        self.assertTrue(any(e['unresolved'] for e in self.hr.employees(include_unresolved=True)))
    def test_export_ignores_pagination_and_escapes_spreadsheet_formulas(self):
        for i in range(60):self.db.users.insert_one({'username':f'export-{i}','first_name':'=1+1','role':'user'})
        output=self.hr.csv_export({'start':'2020-01-06','end':'2020-01-06','page':'2','limit':'1'})
        records=list(csv.reader(io.StringIO(output.lstrip('\ufeff')),delimiter=';'))
        self.assertEqual(len(records),62)
        self.assertTrue(any("'=1+1" in r for r in records))
        self.assertIn('Netto seconden',records[0])
    def test_historic_username_cannot_be_reassigned_to_another_identity(self):
        self.hr.remember_username('synthetic.user','renamed.synthetic',self.uid)
        with self.assertRaises(HRError):
            self.hr.remember_username('other.synthetic','synthetic.user','other-id')
        self.assertEqual(self.hr.resolve({'username':'synthetic.user'}),self.uid)


class APIRoleTests(unittest.TestCase):
    def setUp(self):
        self.db=mongomock.MongoClient().hr_api
        with patch('app.PyMongo',return_value=SimpleNamespace(db=self.db)):self.app=create_app()
        self.app.config.update(TESTING=True,JWT_SECRET_KEY='synthetic-jwt-key-at-least-thirty-two-characters')
        self.client=self.app.test_client();self.tokens={};self.ids={}
        for role in ('user','hr','technical_admin'):
            uid=self.db.users.insert_one({'username':'synthetic.'+role,'email':role+'@example.invalid','role':role,'blocked':False}).inserted_id
            self.ids[role]=str(uid)
            with self.app.app_context():self.tokens[role]=create_access_token(identity='synthetic.'+role,additional_claims={'role':role,'employee_id':str(uid)})
    def headers(self,role):return {'Authorization':'Bearer '+self.tokens[role],'X-TimeTracking-Public-Request':'1','Idempotency-Key':identifier()}
    def test_hr_can_review_without_technical_administration(self):
        self.assertEqual(self.client.get('/api/v1/hr/overview?start=2020-01-01&end=2020-01-01',headers=self.headers('hr')).status_code,200)
        self.assertEqual(self.client.get('/api/v1/hr/system',headers=self.headers('hr')).status_code,403)
        self.assertEqual(self.client.post('/api/v1/users/',headers=self.headers('hr'),json={}).status_code,403)
    def test_technical_role_has_no_hr_access(self):
        self.assertEqual(self.client.get('/api/v1/hr/config',headers=self.headers('technical_admin')).status_code,403)
        self.assertEqual(self.client.get('/api/v1/hr/system',headers=self.headers('technical_admin')).status_code,200)
        self.assertEqual(self.client.get('/api/v1/dashboard/summary',headers=self.headers('technical_admin')).status_code,403)
    def test_employee_has_no_web_access_even_with_a_preexisting_token(self):
        self.assertEqual(self.client.get('/api/v1/hr/details/'+self.ids['user']+'?start=2020-01-01&end=2020-01-01',headers=self.headers('user')).status_code,403)
        self.assertEqual(self.client.get('/api/v1/hr/details/'+self.ids['hr']+'?start=2020-01-01&end=2020-01-01',headers=self.headers('user')).status_code,403)
        self.assertEqual(self.client.post('/api/v1/hr/corrections',headers=self.headers('user'),json={}).status_code,403)
        self.assertEqual(self.client.post('/api/v1/badges/',headers=self.headers('user'),json={'action':'START'}).status_code,403)
        response=self.client.post('/api/v1/hr/requests',headers=self.headers('user'),json={'revision':0,'reason':'Synthetic missing start','proposed':{'action':'START','local_time':'2020-01-01T08:00'}})
        self.assertEqual(response.status_code,403,response.json)
    def test_blocked_account_and_stale_role_claims_are_rechecked(self):
        self.db.users.update_one({'_id':ObjectId(self.ids['hr'])},{'$set':{'role':'user'}})
        self.assertEqual(self.client.get('/api/v1/hr/config',headers=self.headers('hr')).status_code,403)
        self.db.users.update_one({'_id':ObjectId(self.ids['user'])},{'$set':{'blocked':True}})
        self.assertEqual(self.client.get('/api/v1/hr/me',headers=self.headers('user')).status_code,401)
    def test_employee_cannot_read_another_badge_event(self):
        own=self.db.badge_logs.insert_one(event('START','2020-01-01T08:00Z',employee_id=self.ids['hr'])).inserted_id
        response=self.client.get('/api/v1/badges/'+str(own),headers=self.headers('user'))
        self.assertEqual(response.status_code,403)
        response=self.client.get('/api/v1/badges/',headers=self.headers('user'))
        self.assertEqual(response.status_code,403)

    def test_internal_network_alone_is_not_an_authorization(self):
        self.assertEqual(self.client.post('/api/v1/badges/',json={'action':'START'}).status_code,401)
        self.assertEqual(self.client.get('/api/v1/users/').status_code,401)

    def test_existing_branding_and_events_survive_hr_initialization(self):
        self.db.app_settings.insert_one({'key':'branding','value':{'brand_name':'Synthetic company','accent_color':'#123456'}})
        self.db.badge_logs.insert_one(event('START',datetime(2020,1,1,8),employee_id=self.ids['user']))
        before=list(self.db.badge_logs.find({}))
        with patch('app.PyMongo',return_value=SimpleNamespace(db=self.db)):upgraded=create_app()
        self.assertEqual(before,list(self.db.badge_logs.find({})))
        self.assertEqual(upgraded.test_client().get('/api/v1/settings/branding').json['data']['brand_name'],'Synthetic company')


class AutomaticPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('hr_auto_policy',ROOT/'bin/backend/scripts/auto_stop_missing_badges.py')
        cls.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.module)
    def setUp(self):
        self.db=mongomock.MongoClient().automatic_synthetic
        self.db.users.insert_one({'username':'synthetic.user','role':'user'})
        self.start=datetime(2020,1,6,7)
        self.db.badge_logs.insert_one(event('START',self.start))
        self.hr=HRService(self.db)
    def run_mode(self,mode=None):
        if mode:
            self.hr.setting('policy',{'revision':self.hr.state()['revision'],'reason':'Synthetic automatic rule',
                'effective_from':'2020-01-01','rules':{**DEFAULT_RULES,'auto_stop_mode':mode,'auto_stop_hours':6}},'synthetic.hr',identifier())
        from contextlib import redirect_stdout
        with redirect_stdout(io.StringIO()):
            return self.module.run_day(self.db.badge_logs,datetime(2020,1,6),8,datetime(2020,1,7),False,self.hr)
    def test_upgrade_without_new_policy_keeps_eight_elapsed_hours(self):
        self.assertEqual(self.run_mode(),1)
        self.assertEqual(self.db.badge_logs.find_one({'action':'STOP'})['timestamp'],self.start+timedelta(hours=8))
    def test_signal_mode_does_not_insert_stop(self):
        self.run_mode('signal');self.assertEqual(self.db.badge_logs.count_documents({'action':'STOP'}),0)
    def test_proposal_mode_is_idempotent_and_does_not_change_hours(self):
        self.run_mode('propose');self.run_mode()
        self.assertEqual(self.db.badge_logs.count_documents({'action':'STOP'}),0)
        self.assertEqual(len(self.hr.state()['proposals']),1)
    def test_explicit_automatic_mode_uses_configured_elapsed_rule(self):
        self.assertEqual(self.run_mode('automatic'),1)
        stop=self.db.badge_logs.find_one({'action':'STOP'})
        self.assertEqual(stop['timestamp'],self.start+timedelta(hours=6))
        self.assertEqual(stop['raw_data']['reason'],'configured_auto_stop')
    def test_new_policy_does_not_close_a_session_already_stopped_next_day(self):
        self.db.badge_logs.insert_one(event('STOP',datetime(2020,1,7,0)))
        self.run_mode('automatic')
        self.assertEqual(self.db.badge_logs.count_documents({'action':'STOP'}),1)


if __name__=='__main__':unittest.main()
