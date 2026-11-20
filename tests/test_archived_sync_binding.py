"""Archiving releases a live UUID reservation without deleting historical data."""
import unittest
import test_simple_time as fixtures


class ArchivedBindingTests(unittest.TestCase):
    setUp=fixtures.SimpleTimeTests.setUp
    configure=fixtures.SimpleTimeTests.configure
    run_sync=fixtures.SimpleTimeTests.run_sync

    def old_account(self,archived=True,blocked=True):
        old=str(self.db.users.insert_one({'username':'synthetic.old','role':'user',
            'archived':archived,'blocked':blocked}).inserted_id)
        binding={'uuid':fixtures.UUID,'name':'synthetic.employee','server':fixtures.SERVER}
        self.db.loxone_sync_config.update_one({'_id':'settings'},{'$set':{'bindings':{old:binding}}})
        self.db.badge_logs.insert_one({'employee_id':old,'username':'synthetic.old','action':'START','timestamp':'2026-11-10T08:00Z'})
        self.db.badge_logs.insert_one({'employee_id':old,'username':'synthetic.old','action':'STOP','timestamp':'2026-11-10T15:25Z'})
        return old,binding

    def test_archived_account_keeps_history_and_binding_but_does_not_block_new_writer(self):
        self.configure();old,binding=self.old_account();history=list(self.db.badge_logs.find({'employee_id':old}))
        result=self.run_sync()
        self.assertEqual(result['writes'],1)
        self.assertEqual(self.sync.config()['bindings'][old],binding)
        self.assertEqual(self.sync.config()['bindings'][self.uid]['uuid'],fixtures.UUID)
        self.assertEqual(list(self.db.badge_logs.find({'employee_id':old})),history)
        self.assertEqual(self.bridge.fields['customField1'],'0')
        rows=self.sync.preview(fixtures.NOW,remote=False)['rows']
        self.assertEqual([row['employee']['id'] for row in rows],[self.uid])

    def test_active_or_only_blocked_account_still_reserves_uuid(self):
        for blocked in (False,True):
            with self.subTest(blocked=blocked):
                self.setUp();self.configure();self.old_account(archived=False,blocked=blocked)
                result=self.run_sync()
                self.assertGreater(result['failed'],0);self.assertFalse(self.bridge.writes)

    def test_explicit_recheck_ignores_archived_reservation(self):
        self.configure();old,_=self.old_account();self.run_sync()
        self.db.loxone_sync_status.update_one({'_id':self.uid},{'$set':{'quarantined':True,'error_code':'verification'}},upsert=True)
        before=len(self.bridge.writes)
        result=self.sync.recheck({'revision':self.sync.config()['revision'],'employee_id':self.uid,
            'reason':'Synthetic archive recovery'},'synthetic.admin')
        self.assertTrue(result['verified']);self.assertEqual(len(self.bridge.writes),before)
        self.assertFalse(self.db.loxone_sync_status.find_one({'_id':self.uid})['quarantined'])
        self.assertTrue(self.db.users.find_one({'username':'synthetic.old'})['archived'])

    def test_unarchiving_restores_conflict_protection(self):
        self.configure();old,_=self.old_account();self.run_sync()
        from bson import ObjectId
        self.db.users.update_one({'_id':ObjectId(old)},{'$set':{'archived':False}})
        self.bridge.calls=[];self.sync.request_sync('synthetic.admin')
        self.assertGreater(self.run_sync()['failed'],0);self.assertFalse(self.bridge.writes)


if __name__=='__main__':unittest.main()
