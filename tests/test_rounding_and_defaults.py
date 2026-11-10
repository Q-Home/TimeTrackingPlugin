"""Rounding/default-regime regressions with synthetic records only."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import mongomock
from bson import ObjectId
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'bin/backend'))
from app.hr.engine import calculate, expected, DEFAULT_RULES, rounded_instant, instant
from app.hr.service import HRService, HRError, identifier

NOW = datetime(2026, 11, 12, 18, tzinfo=timezone.utc)

class RoundingTests(unittest.TestCase):
    def setUp(self):
        self.employee = {'id':'synthetic', 'department':'Test'}
        self.state = {'default_regime_from':'2026-11-01', 'assignments':[],
                      'schedules':[], 'calendar':[], 'policies':[]}
    def events(self, pairs, on='2026-11-09'):
        return [{'_id':str(i), 'action':action, 'timestamp':on+'T'+clock+'+01:00'}
                for i, (action, clock) in enumerate(pairs)]
    def calc(self, pairs, **kw):
        return calculate(self.events(pairs), self.state, self.employee,
                         date(2026,11,9), date(2026,11,9), now=kw.get('now',NOW))
    def rules(self, **rules):
        self.state['policies'] = [{'effective_from':'2026-11-01', 'rules':{**DEFAULT_RULES, **rules}}]
    def test_requested_example_and_raw_records_unchanged(self):
        events=self.events([('START','07:26'),('STOP','16:34')]);before=deepcopy(events)
        row=calculate(events,self.state,self.employee,date(2026,11,9),date(2026,11,9),now=NOW)['days'][0]
        self.assertEqual(row['work_seconds'],9*3600)
        self.assertEqual(events,before)
        self.assertEqual(row['events'][0]['timestamp'],'2026-11-09T06:26:00Z')
        self.assertEqual(row['events'][0]['calculation_timestamp'],'2026-11-09T06:30:00Z')
        self.assertEqual(row['events'][1]['calculation_timestamp'],'2026-11-09T15:30:00Z')
    def test_rounding_disabled_uses_seconds(self):
        self.rules(rounding_minutes=0)
        row=self.calc([('START','07:26:12'),('STOP','16:34:48')])['days'][0]
        self.assertEqual(row['work_seconds'],9*3600+8*60+36)
        self.assertNotIn('calculation_timestamp',row['events'][0])
    def test_all_grid_steps_and_directions(self):
        for step in (1,5,10,15,30,60):
            rules={**DEFAULT_RULES,'rounding_minutes':step}
            value=instant('2026-11-09T07:26:30+01:00')
            for direction in ('up','down','nearest'):
                result=rounded_instant(value,rules,direction)
                self.assertEqual((result.astimezone(__import__('zoneinfo').ZoneInfo('Europe/Brussels')).minute)%step if step<60 else result.minute,0)
                self.assertEqual(result.second,0)
                if direction=='up': self.assertGreaterEqual(result,value)
                if direction=='down': self.assertLessEqual(result,value)
    def test_nearest_midpoint_goes_up_and_exact_boundary_stays(self):
        rules={**DEFAULT_RULES,'rounding_minutes':5}
        self.assertEqual(rounded_instant(instant('2026-11-09T07:27:30Z'),rules,'nearest'),instant('2026-11-09T07:30Z'))
        for direction in ('up','down','nearest'):
            self.assertEqual(rounded_instant(instant('2026-11-09T07:30Z'),rules,direction),instant('2026-11-09T07:30Z'))
    def test_actual_break_is_exact_and_only_outer_boundaries_round(self):
        row=self.calc([('START','07:26'),('BREAK','12:02'),('RETURN','12:33'),('STOP','16:34')])['days'][0]
        self.assertEqual(row['break_seconds'],31*60)
        self.assertEqual(row['work_seconds'],9*3600-31*60)
        self.assertNotIn('calculation_timestamp',row['events'][1])
    def test_automatic_break_deducted_after_rounding(self):
        self.rules(break_mode='automatic',automatic_break_minutes=30)
        row=self.calc([('START','07:26'),('STOP','16:34')])['days'][0]
        self.assertEqual(row['work_seconds'],8.5*3600)
        self.assertEqual(row['automatic_break_seconds'],1800)
    def test_short_session_never_becomes_negative(self):
        row=self.calc([('START','07:26'),('STOP','07:29')])['days'][0]
        self.assertEqual(row['work_seconds'],0)
        self.assertEqual(row['periods'],[])
    def test_inward_rounding_across_break_does_not_overcount(self):
        row=self.calc([('START','07:26'),('BREAK','07:27'),('RETURN','07:28'),('STOP','07:29')])['days'][0]
        self.assertEqual(row['work_seconds'],0); self.assertEqual(row['break_seconds'],0)
    def test_multiple_sessions_and_outward_overlap_not_double_counted(self):
        self.rules(rounding_start='down',rounding_stop='up')
        row=self.calc([('START','07:01'),('STOP','07:04'),('START','07:04:30'),('STOP','07:06')])['days'][0]
        self.assertEqual(row['work_seconds'],10*60)
    def test_live_start_rounds_but_current_time_does_not(self):
        row=self.calc([('START','07:26')],now=instant('2026-11-09T07:32+01:00'))['days'][0]
        self.assertEqual(row['work_seconds'],120); self.assertTrue(row['provisional'])
        row=self.calc([('START','07:26')],now=instant('2026-11-09T07:28+01:00'))['days'][0]
        self.assertEqual(row['work_seconds'],0)
    def test_live_pause_preserves_completed_work(self):
        row=self.calc([('START','07:26'),('BREAK','12:02')],now=instant('2026-11-09T12:40+01:00'))['days'][0]
        self.assertEqual(row['work_seconds'],(4*60+32)*60)
        self.assertEqual(row['break_seconds'],38*60)
    def test_overnight_and_midnight_grid(self):
        events=[{'_id':'a','action':'START','timestamp':'2026-11-09T23:58+01:00'},
                {'_id':'b','action':'STOP','timestamp':'2026-11-10T08:04+01:00'}]
        result=calculate(events,self.state,self.employee,date(2026,11,9),date(2026,11,10),now=NOW)
        self.assertEqual([d['work_seconds'] for d in result['days']],[0,8*3600])
    def test_dst_preserves_real_elapsed_hours_and_fold(self):
        self.state['default_regime_from']='2026-01-01'
        for on,start,stop,hours in [('2026-03-29','01:56+01:00','04:04+02:00',1),('2026-10-25','01:56+02:00','04:04+01:00',3)]:
            events=[{'_id':'a','action':'START','timestamp':on+'T'+start},{'_id':'b','action':'STOP','timestamp':on+'T'+stop}]
            row=calculate(events,self.state,self.employee,date.fromisoformat(on),date.fromisoformat(on),now=NOW)['days'][0]
            self.assertEqual(row['work_seconds'],hours*3600)
    def test_policy_changes_use_each_boundary_date(self):
        self.state['policies']=[{'effective_from':'2026-11-10','rules':{'rounding_minutes':15,'rounding_stop':'down'}}]
        events=[{'_id':'a','action':'START','timestamp':'2026-11-09T23:56+01:00'},
                {'_id':'b','action':'STOP','timestamp':'2026-11-10T08:14+01:00'}]
        result=calculate(events,self.state,self.employee,date(2026,11,9),date(2026,11,10),now=NOW)
        self.assertEqual(result['summary']['work_seconds'],8*3600)
    def test_legacy_days_unchanged_before_activation(self):
        self.state['default_regime_from']='2026-11-10'
        row=self.calc([('START','07:26'),('STOP','16:34')])['days'][0]
        self.assertEqual(row['work_seconds'],9*3600+8*60);self.assertIsNone(row['expected_seconds'])
        self.assertNotIn('calculation_timestamp',row['events'][0])
    def test_default_is_40_hour_week_with_free_weekend(self):
        result=calculate([],self.state,self.employee,date(2026,11,9),date(2026,11,15),now=instant('2026-11-16T12:00Z'))
        self.assertEqual([d['expected_seconds'] for d in result['days']],[28800]*5+[0,0])
        self.assertEqual(result['summary']['expected_seconds'],40*3600)
    def test_personal_schedule_and_calendar_override_default(self):
        self.state['schedules']=[{'id':'part','days':[{'minutes':240}]*7}]
        self.state['assignments']=[{'employee_id':'synthetic','schedule_id':'part','effective_from':'2026-11-10'}]
        self.assertEqual(expected(self.state,self.employee,date(2026,11,9)),28800)
        self.assertEqual(expected(self.state,self.employee,date(2026,11,10)),14400)
        self.state['calendar']=[{'start':'2026-11-09','end':'2026-11-09','effect':'zero'},
            {'start':'2026-11-10','end':'2026-11-10','effect':'hours','minutes':120,'employee_id':'synthetic'}]
        self.assertEqual(expected(self.state,self.employee,date(2026,11,9)),0)
        self.assertEqual(expected(self.state,self.employee,date(2026,11,10)),7200)
    def test_default_can_be_changed_or_disabled_with_date(self):
        self.rules(default_workday_minutes=360)
        self.assertEqual(expected(self.state,self.employee,date(2026,11,9)),21600)
        self.rules(default_workday_minutes=0)
        self.assertIsNone(expected(self.state,self.employee,date(2026,11,9)))

class UpgradeAndPolicyTests(unittest.TestCase):
    def setUp(self):
        self.db=mongomock.MongoClient().synthetic_rounding
        self.hr=HRService(self.db)
        self.uid=str(self.db.users.insert_one({'role':'user','username':'synthetic'}).inserted_id)
    def save(self, **rules):
        return self.hr.setting('policy',{'revision':self.hr.state()['revision'],'reason':'Synthetic policy',
            'effective_from':'2026-11-09','rules':{**DEFAULT_RULES,**rules}},'synthetic.hr',identifier())
    def test_upgrade_is_persistent_idempotent_and_audited(self):
        with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(lambda _:self.hr.initialize_defaults(),range(6)))
        state=self.hr.state();self.assertTrue(state['default_regime_from'])
        self.assertEqual(sum(a['kind']=='default_regime' for a in state['audit']),1)
        second=HRService(self.db);second.initialize_defaults();self.assertEqual(state,second.state())
    def test_upgrade_preserves_closed_historical_calculation_hash(self):
        state=self.hr.state();on='2020-01-06'
        self.db.badge_logs.insert_many([{'employee_id':self.uid,'_id':ObjectId(),'action':a,'timestamp':on+'T'+t+'Z'} for a,t in [('START','07:26'),('STOP','16:34')]])
        state['approvals']=[{'id':'synthetic','employee_id':self.uid,'start':on,'end':on,'status':'closed'}]
        self.db.hr_state.insert_one(state)
        before=self.hr.calculation_hash(self.uid,date(2020,1,6),date(2020,1,6),state)
        self.hr.initialize_defaults()
        self.assertEqual(before,self.hr.calculation_hash(self.uid,date(2020,1,6),date(2020,1,6),self.hr.state()))
    def test_upgrade_starts_after_any_existing_protected_period(self):
        state=self.hr.state();state['approvals']=[{'start':'2090-01-01','end':'2090-01-04','status':'closed'}]
        self.db.hr_state.insert_one(state);self.hr.initialize_defaults()
        self.assertEqual(self.hr.state()['default_regime_from'],'2090-01-05')
    def test_policy_validation_rejects_invalid_rounding_and_norm(self):
        for rules in ({'rounding_minutes':True},{'rounding_minutes':7},{'rounding_minutes':5.0},{'rounding_minutes':-5},
                      {'rounding_start':'sideways'},{'rounding_stop':[]},{'default_workday_minutes':-1},
                      {'default_workday_minutes':True},{'default_workday_minutes':480.5}):
            with self.subTest(rules=rules),self.assertRaises(HRError):self.save(**rules)
    def test_saved_policy_audits_and_preserves_rounding_options(self):
        self.save(rounding_minutes=15,rounding_start='nearest',rounding_stop='up')
        self.assertEqual(self.hr.settings_view()['policies'][0]['rules']['rounding_minutes'],15)
        self.assertEqual(self.hr.state()['audit'][-1]['actor'],'synthetic.hr')
    def test_backdating_over_approval_is_blocked(self):
        state=self.hr.state();state['approvals']=[{'employee_id':self.uid,'start':'2026-11-09','end':'2026-11-09','status':'approved'}]
        self.db.hr_state.insert_one(state)
        with self.assertRaises(HRError):self.save(rounding_minutes=10)

if __name__=='__main__':unittest.main()
