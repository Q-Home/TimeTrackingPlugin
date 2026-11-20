"""Stored sync failures and proven legacy ID aliases; synthetic identities only."""
from copy import deepcopy
from datetime import timedelta
import unittest
import test_simple_time as fixtures
from app.loxone_sync.bridge import SyncError

UUID=fixtures.UUID
NOW=fixtures.NOW


class RecheckTests(unittest.TestCase):
    setUp=fixtures.SimpleTimeTests.setUp
    events=fixtures.SimpleTimeTests.events
    configure=fixtures.SimpleTimeTests.configure
    run_sync=fixtures.SimpleTimeTests.run_sync

    def pause(self):
        self.db.loxone_sync_status.update_one({'_id':self.uid},{'$set':{
            'quarantined':True,'error_code':'verification','last_error':'Old generic custom-field mismatch',
            'retry_at':NOW-timedelta(days=1),'failures':1}},upsert=True)

    def recheck(self):
        return self.sync.recheck({'revision':self.sync.config()['revision'],'employee_id':self.uid,
            'reason':'Synthetic explicit same-UUID recheck'},'synthetic.admin')

    def test_numeric_userid_and_uuid_can_be_proven_to_be_one_user(self):
        self.events([('START','07:00'),('STOP','15:00')],user_id='1234')
        self.configure();self.assertEqual(self.run_sync()['writes'],1)
        binding=self.sync.config()['bindings'][self.uid]
        self.assertEqual(binding['uuid'],UUID)
        self.assertEqual(binding['source_keys'],['id:1234','uuid:'+UUID.replace('-','')])
        self.assertEqual(self.bridge.fields['customField1'],'8')

    def test_conflicting_aliases_never_overwrite_an_existing_link(self):
        self.configure();self.run_sync();old=deepcopy(self.sync.config()['bindings'][self.uid])
        other='22345678-1234-1234-1234567890abcdef'
        self.bridge.users.append({'uuid':other,'name':'synthetic.other'});self.bridge.ids['OTHER']=other
        self.events([('START','07:00')],user_id='OTHER')
        self.pause();before=len(self.bridge.writes)
        with self.assertRaises(SyncError):self.recheck()
        self.assertEqual(len(self.bridge.writes),before)
        self.assertEqual(self.sync.config()['bindings'][self.uid],old)
        self.assertTrue(self.db.loxone_sync_status.find_one({'_id':self.uid})['quarantined'])

    def test_shared_alias_blocks_both_local_employees(self):
        self.events([('START','07:00')],user_id='1234')
        self.db.users.insert_one({'username':'synthetic.second','role':'user','user_id':'1234'})
        self.configure();result=self.run_sync()
        self.assertEqual(result['failed'],2);self.assertFalse(self.bridge.writes)
        self.assertEqual(self.sync.config()['bindings'],{})

    def test_historic_pause_is_visible_and_does_not_retry_automatically(self):
        self.configure();self.run_sync();self.pause();before=len(self.bridge.writes)
        self.sync.request_sync('synthetic.admin');self.run_sync()
        self.assertEqual(len(self.bridge.writes),before)
        row=self.sync.preview(NOW,remote=False)['rows'][0]
        self.assertTrue(row['quarantined'])
        self.assertIn('gepauzeerd',row['link_status'])
        self.assertNotIn('Old generic',row['last_error'])

    def test_explicit_recheck_reads_same_uuid_then_resumes_numeric_delivery(self):
        self.configure();self.run_sync();self.pause()
        self.bridge.fields['customField1']='Niet beschikbaar';before=len(self.bridge.writes)
        result=self.recheck()
        self.assertTrue(result['verified']);self.assertEqual(len(self.bridge.writes),before)
        status=self.db.loxone_sync_status.find_one({'_id':self.uid})
        self.assertFalse(status['quarantined']);self.assertIsNone(status['last_error'])
        self.assertEqual(self.run_sync()['writes'],1)
        self.assertEqual(self.bridge.fields['customField1'],'0')
        self.assertEqual(self.db.loxone_sync_audit.count_documents({'kind':'binding_rechecked'}),1)

    def test_failed_network_recheck_keeps_quarantine(self):
        self.configure();self.run_sync();self.pause();self.bridge.error='network'
        with self.assertRaises(SyncError):self.recheck()
        self.assertTrue(self.db.loxone_sync_status.find_one({'_id':self.uid})['quarantined'])

    def test_changed_alias_during_read_still_blocks_write(self):
        self.events([('START','07:00'),('STOP','15:00')],user_id='1234')
        self.configure();original=self.bridge.call
        def changing(operation,server=None,**data):
            value=original(operation,server,**data)
            if operation=='user':self.events([('SCAN','14:00')],user_id='NEW-UNVERIFIED')
            return value
        self.bridge.call=changing
        self.assertEqual(self.run_sync()['failed'],1);self.assertFalse(self.bridge.writes)


if __name__=='__main__':unittest.main()
