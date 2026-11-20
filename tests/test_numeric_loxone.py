"""Numeric custom-field delivery through the real sync worker; no network."""
from datetime import timedelta
import unittest
import test_loxone_sync as fixtures
from test_loxone_sync import NOW, FIELDS
from app.loxone_sync.service import decimal_hours


class NumericLoxoneTests(unittest.TestCase):
    setUp=fixtures.SyncTests.setUp
    configure=fixtures.SyncTests.configure
    link=fixtures.SyncTests.link
    run_sync=fixtures.SyncTests.run_sync
    events=fixtures.SyncTests.events

    def test_decimal_hours_uses_dot_and_preserves_negative_balance(self):
        for seconds,expected in [(0,'0'),(27000,'7.5'),(26700,'7.416667'),(-1800,'-0.5'),(36000,'10'),(-0.00001,'0')]:
            self.assertEqual(decimal_hours(seconds),expected)
        for value in (None,float('nan'),float('inf'),'not available'):
            self.assertEqual(decimal_hours(value),'0')

    def test_actual_worker_sends_seven_hours_twenty_five_as_numeric_hours(self):
        self.db.badge_logs.update_one({'action':'START'},{'$set':{'timestamp':'2026-11-09T07:00Z'}})
        self.db.badge_logs.update_one({'action':'STOP'},{'$set':{'timestamp':'2026-11-09T14:55Z'}})
        self.configure(True);self.link()
        preview=self.sync.preview(NOW)['rows'][0]
        self.assertEqual(preview['values']['today'],'7u 25m')
        self.assertEqual(preview['desired']['customField1'],'7.416667')
        self.assertFalse(self.bridge.writes)
        self.run_sync()
        self.assertEqual(self.bridge.fields['customField1'],'7.416667')
        self.assertEqual(self.bridge.fields['customField2'],str(int(NOW.timestamp())))

    def test_unavailable_data_is_written_as_zero_with_diagnostics_retained(self):
        self.db.badge_logs.delete_many({})
        self.configure(True);self.link()
        totals=self.sync.totals(self.uid,NOW)
        self.assertIsNone(totals['values']['today'])
        self.assertEqual(totals['loxone_values']['today'],'0')
        self.assertTrue(totals['issues']['today'])
        self.run_sync()
        self.assertEqual(self.bridge.fields['customField1'],'0')
        self.assertNotIn('Niet beschikbaar',str(self.bridge.writes))

    def test_all_five_selected_fields_are_numeric_and_balance_has_ascii_minus(self):
        self.hr.initialize_simple_mode()
        mapping=dict(zip(FIELDS,('today','week','month','balance','status')))
        self.configure(True,mapping=mapping);self.link();self.run_sync()
        fields=self.bridge.writes[-1][1]['fields']
        self.assertEqual(set(fields),set(FIELDS))
        for value in fields.values():self.assertRegex(value,r'^-?[0-9]+(?:\.[0-9]+)?$')
        self.assertTrue(fields['customField4'].startswith('-'))
        self.assertEqual(fields['customField5'],'3')

    def test_live_hours_stay_numeric_without_provisional_suffix(self):
        self.db.badge_logs.delete_one({'action':'STOP'})
        self.configure(True);self.link();self.run_sync()
        self.assertRegex(self.bridge.fields['customField1'],r'^[0-9]+(?:\.[0-9]+)?$')
        totals=self.sync.totals(self.uid,NOW)
        self.assertIn('voorlopig',totals['values']['today'])
        self.assertEqual(totals['loxone_values']['status'],'1')

    def test_numeric_status_codes_are_stable(self):
        self.assertEqual(self.sync.totals(self.uid,NOW)['loxone_values']['status'],'3')
        self.hr.initialize_simple_mode()
        self.db.badge_logs.update_one({'action':'STOP'},{'$set':{'raw_data':{'auto_stop':True}}})
        self.assertEqual(self.sync.totals(self.uid,NOW)['loxone_values']['status'],'4')
        self.db.badge_logs.delete_one({'action':'STOP'})
        self.assertEqual(self.sync.totals(self.uid,NOW)['loxone_values']['status'],'1')
        self.db.badge_logs.insert_one({'employee_id':self.uid,'action':'BREAK','timestamp':'2026-11-09T14:45Z'})
        self.assertEqual(self.sync.totals(self.uid,NOW)['loxone_values']['status'],'2')
        self.db.badge_logs.delete_many({})
        self.assertEqual(self.sync.totals(self.uid,NOW)['loxone_values']['status'],'0')

    def test_old_text_timestamp_is_migrated_without_advancing_content_time(self):
        self.configure(True);self.link();self.run_sync()
        first=self.bridge.fields['customField2']
        self.bridge.fields['customField2']='09/11/2026 16:00'
        self.run_sync(NOW+timedelta(minutes=10))
        self.assertEqual(self.bridge.fields['customField2'],first)
        self.run_sync(NOW+timedelta(minutes=20))
        self.assertEqual(len(self.bridge.writes),2)


if __name__=='__main__':unittest.main()
