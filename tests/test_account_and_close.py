"""Synthetic account and overnight scheduling regressions; no live host writes."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import importlib.util
import io
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

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bin/backend'))
os.environ.setdefault('JWT_SECRET_KEY','synthetic-test-key-more-than-thirty-two-characters')
os.environ.setdefault('MONGO_URI','mongodb://localhost/synthetic_account_tests')
from app import create_app
from app.hr.engine import DEFAULT_RULES
from app.hr.service import HRService,HRError,identifier
from app.repositories.user_repository import UserRepository


class AccountPasswordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.old_hash=bcrypt.hashpw(b'synthetic-old-password',bcrypt.gensalt()).decode()
    def setUp(self):
        self.db=mongomock.MongoClient().synthetic_accounts
        with patch('app.PyMongo',return_value=SimpleNamespace(db=self.db)):self.app=create_app()
        self.app.config.update(TESTING=True,JWT_SECRET_KEY='synthetic-secret-more-than-thirty-two-characters')
        self.client=self.app.test_client();self.ids={};self.tokens={}
        for role in ('user','hr','technical_admin'):
            uid=self.db.users.insert_one({'username':'synthetic.'+role,'email':role+'@example.invalid','role':role,'password':self.old_hash,'blocked':False}).inserted_id
            self.ids[role]=str(uid)
            with self.app.app_context():self.tokens[role]=create_access_token(identity='synthetic.'+role,additional_claims={'employee_id':str(uid),'role':role})
    def change(self,role='user',target=None,**data):
        return self.client.put('/api/v1/users/'+(target or self.ids[role])+'/password',json=data,
            headers={'Authorization':'Bearer '+self.tokens[role]})
    def test_employee_changes_own_password_and_old_login_stops_working(self):
        response=self.change(password=' synthetic new password ',current_password='synthetic-old-password')
        self.assertEqual(response.status_code,200,response.json)
        for password,status in [('synthetic-old-password',401),(' synthetic new password ',200)]:
            self.assertEqual(self.client.post('/api/v1/login',json={'username':'synthetic.user','password':password}).status_code,status)
    def test_missing_or_wrong_current_password_does_not_change_hash(self):
        for current in (None,'wrong'):
            response=self.change(password='synthetic-new-password',current_password=current)
            self.assertEqual(response.status_code,400)
        self.assertEqual(self.db.users.find_one({'_id':ObjectId(self.ids['user'])})['password'],self.old_hash)
    def test_employee_and_hr_cannot_change_other_accounts(self):
        for role in ('user','hr'):
            self.assertEqual(self.change(role,target=self.ids['technical_admin'],password='synthetic-new-password').status_code,403)
    def test_technical_reset_of_other_user_remains_available(self):
        self.assertEqual(self.change('technical_admin',target=self.ids['user'],password='synthetic-reset-password').status_code,200)
        self.assertEqual(self.change('technical_admin',password='synthetic-new-password').status_code,400)
    def test_invalid_passwords_do_not_write(self):
        for value in ('short',' '*6,'é'*37,12345):
            self.assertEqual(self.change(password=value,current_password='synthetic-old-password').status_code,400)
    def test_blocked_and_anonymous_accounts_are_rejected(self):
        self.db.users.update_one({'_id':ObjectId(self.ids['user'])},{'$set':{'blocked':True}})
        self.assertEqual(self.change(password='synthetic-new-password',current_password='synthetic-old-password').status_code,401)
        self.assertEqual(self.client.put('/api/v1/users/'+self.ids['user']+'/password',json={'password':'synthetic-new-password'}).status_code,401)
    def test_password_update_has_a_compare_and_swap(self):
        repository=UserRepository(SimpleNamespace(db=self.db))
        repository.update_password_if_unchanged(self.ids['user'],self.old_hash,{'password':'other-current-hash'})
        result=repository.update_password_if_unchanged(self.ids['user'],self.old_hash,{'password':'must-not-win'})
        self.assertEqual(result.matched_count,0)
        self.assertEqual(self.db.users.find_one({'_id':ObjectId(self.ids['user'])})['password'],'other-current-hash')
    def test_new_main_navigation_and_account_form_are_available(self):
        self.assertIn('account.html',(ROOT/'bin/Webapp/js/hr.js').read_text())
        html=(ROOT/'bin/Webapp/account.html').read_text()
        self.assertIn('autocomplete="current-password"',html);self.assertIn('repeat_password',html)


class FrozenDateTime(datetime):
    @classmethod
    def now(cls,tz=None):
        value=cls(2026,11,9,23,5,tzinfo=timezone.utc)
        return value.astimezone(tz) if tz else value.replace(tzinfo=None)


class NightlyCloseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec=importlib.util.spec_from_file_location('nightly_auto_close',ROOT/'bin/backend/scripts/auto_stop_missing_badges.py')
        cls.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.module)
    def setUp(self):
        self.client=mongomock.MongoClient('mongodb://localhost/customer_synthetic')
        self.db=self.client.customer_synthetic;self.hr=HRService(self.db)
        self.uid=str(self.db.users.insert_one({'username':'synthetic.employee','role':'user'}).inserted_id)
    def event(self,action,when):
        return self.db.badge_logs.insert_one({'action':action,'timestamp':datetime.fromisoformat(when),'username':'synthetic.employee','employee_id':self.uid}).inserted_id
    def night(self,dry_run=False):
        counters={}
        with redirect_stdout(io.StringIO()):
            count=self.module.run(self.db.badge_logs,datetime(2026,11,9),8,2,dry_run,self.hr,
                completed_days=True,run_time=FrozenDateTime.now(timezone.utc),diagnostics=counters)
        return count,counters
    def test_midnight_run_closes_previous_day_at_eight_elapsed_hours(self):
        self.event('START','2026-11-09T08:00');self.event('BREAK','2026-11-09T12:00');self.event('RETURN','2026-11-09T12:30')
        self.assertEqual(self.night()[0],1)
        self.assertEqual(self.db.badge_logs.find_one({'action':'STOP'})['timestamp'],datetime(2026,11,9,16))
        self.assertEqual(self.night()[0],0)
    def test_real_stop_after_midnight_prevents_an_artificial_stop(self):
        self.event('START','2026-11-08T22:00');self.event('STOP','2026-11-09T06:00')
        self.assertEqual(self.night()[0],0)
        self.assertEqual(self.db.badge_logs.count_documents({'action':'STOP'}),1)
    def test_two_completed_start_days_are_caught_up_in_order(self):
        self.event('START','2026-11-08T08:00');self.event('START','2026-11-09T08:00')
        self.assertEqual(self.night()[0],2)
        self.assertEqual([e['timestamp'] for e in self.db.badge_logs.find({'action':'STOP'}).sort('timestamp',1)],
            [datetime(2026,11,8,16),datetime(2026,11,9,16)])
    def test_hr_overlay_and_deleted_start_are_respected(self):
        start=self.event('START','2026-11-09T08:00')
        self.hr.correct({'revision':0,'employee_id':self.uid,'new':{'action':'STOP','timestamp':'2026-11-09T16:00Z'},'reason':'Synthetic completed shift'},'synthetic.hr',identifier())
        self.assertEqual(self.night()[0],0)
        self.db.hr_state.delete_many({})
        self.hr.correct({'revision':0,'employee_id':self.uid,'target_id':str(start),'new':None,'reason':'Synthetic voided start'},'synthetic.hr',identifier())
        self.assertEqual(self.night()[0],0)
    def test_future_end_and_current_day_are_not_closed(self):
        self.event('START','2026-11-09T22:00')
        count,counters=self.night();self.assertEqual(count,0);self.assertEqual(counters['future_end'],1)
        self.db.badge_logs.delete_many({});self.event('START','2026-11-09T23:01') # Nov 10 locally
        self.assertEqual(self.night()[0],0)
    def test_night_policy_still_supports_signal_and_propose(self):
        self.event('START','2026-11-09T08:00')
        for mode,key in [('signal','signalled'),('propose','proposed')]:
            self.hr.setting('policy',{'revision':self.hr.state()['revision'],'effective_from':'2026-01-01',
                'rules':{**DEFAULT_RULES,'auto_stop_mode':mode},'reason':'Synthetic close policy'},'synthetic.hr',identifier())
            count,counters=self.night();self.assertEqual(count,0);self.assertEqual(counters[key],1)
        self.assertEqual(len(self.hr.state()['proposals']),1)
    def test_dry_run_does_not_write(self):
        self.event('START','2026-11-09T08:00');self.assertEqual(self.night(True)[0],1)
        self.assertEqual(self.db.badge_logs.count_documents({'action':'STOP'}),0)
    def test_period_guard_is_visible_and_database_failure_is_not_hidden(self):
        self.event('START','2026-11-09T08:00')
        with patch.object(self.hr,'reserve_event',side_effect=HRError('Synthetic closed period',409)):
            count,counters=self.night();self.assertEqual(count,0);self.assertEqual(counters['blocked_period'],1)
        with patch.object(self.hr,'reserve_event',side_effect=RuntimeError('Synthetic database failure')):
            with self.assertRaises(RuntimeError):self.night()
    def test_cli_uses_uri_database_yesterday_and_timestamped_log(self):
        self.event('START','2026-11-09T08:00');log=io.StringIO()
        with patch.object(self.module,'datetime',FrozenDateTime),patch.object(self.module,'MongoClient',return_value=self.client),patch.object(self.module,'load_env_file'),patch.dict(os.environ,{'MONGO_URI':'mongodb://localhost/customer_synthetic'},clear=True),patch.object(sys,'argv',['auto-close','--completed-days']),redirect_stdout(log):
            self.assertEqual(self.module.main(),0)
        self.assertIn('target=2026-11-09',log.getvalue());self.assertIn('2026-11-09T23:05',log.getvalue())
        self.assertEqual(self.db.badge_logs.count_documents({'action':'STOP'}),1)
        self.assertEqual(self.client.timetracking.badge_logs.count_documents({}),0)
    def test_nightly_bounds_follow_company_timezone_and_dst(self):
        lo,hi=self.module.day_bounds_utc(datetime(2026,3,8),'America/New_York')
        self.assertEqual((hi-lo).total_seconds(),23*3600)
        self.assertEqual(lo,datetime(2026,3,8,5))
    def test_invalid_source_does_not_abort_other_employees(self):
        self.event('START','2026-11-09T08:00')
        self.db.badge_logs.insert_one({'employee_id':self.uid,'username':'synthetic.employee','action':'STOP','timestamp':'invalid'})
        count,counters=self.night();self.assertEqual(count,0);self.assertGreater(counters['invalid_source'],0)
    def test_cron_has_one_locked_nightly_run_and_no_midday_run(self):
        cron=(ROOT/'cron/crontab').read_text()
        entries=[line for line in cron.splitlines() if line and not line.startswith('#') and 'auto_stop_missing_badges.py' in line]
        self.assertEqual(len(entries),1);self.assertTrue(entries[0].startswith('5 0 * * * loxberry flock -n '))
        self.assertIn('--completed-days',entries[0])


if __name__=='__main__':unittest.main()
