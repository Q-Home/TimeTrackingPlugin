"""Synthetic socket envelopes; no Miniserver connection or user writes."""
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import mongomock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bin/backend'))
os.environ.setdefault('MONGO_URI','mongodb://localhost/synthetic_certificate')
from app.hr.service import HRService
from app.loxone_sync.bridge import Bridge, SyncError, TRANSPORT_WARNINGS
from app.loxone_sync.service import SyncService

SERVER={'slot':'1','serial':'AABBCCDDEEFF'}

class CertificateCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.db=mongomock.MongoClient().synthetic_certificate
        self.service=SyncService(self.db,HRService(self.db))
        config=self.service.config();config['server']=SERVER
        self.db.loxone_sync_config.insert_one(config)
    def call(self,envelope,operation='probe',server=SERVER):
        with patch('socket.socket') as sock, patch('socket.AF_UNIX',1,create=True):
            connection=sock.return_value.__enter__.return_value
            connection.recv.return_value=json.dumps(envelope).encode()+b'\n'
            return self.service.bridge.call(operation,server)
    def test_success_with_warning_still_returns_probe_and_persists_diagnosis(self):
        result=self.call({'ok':True,'data':{'server':SERVER},'warnings':['certificate_hostname_mismatch']})
        self.assertEqual(result['server'],SERVER)
        self.assertEqual(result['transport_warnings'][0]['code'],'certificate_hostname_mismatch')
        fresh=SyncService(self.db,HRService(self.db))
        status=fresh.preview(remote=False)['transport']
        self.assertEqual(status['warnings'],result['transport_warnings'])
        self.assertIsNotNone(status['checked_at'])
    def test_successful_verified_connection_clears_warning(self):
        self.call({'ok':True,'data':{},'warnings':['certificate_expired']})
        result=self.call({'ok':True,'data':{},'warnings':[]})
        self.assertEqual(result['transport_warnings'],[])
        self.assertEqual(self.service.preview(remote=False)['transport']['warnings'],[])
    def test_users_list_contract_is_not_changed_by_warning(self):
        result=self.call({'ok':True,'data':[{'uuid':'synthetic','name':'Demo'}],'warnings':['certificate_untrusted']},'users')
        self.assertIsInstance(result,list)
        self.assertEqual(result[0]['name'],'Demo')
        self.assertTrue(self.service.transport_status(SERVER)['warnings'])
    def test_patch_contract_and_no_success_failure_counter(self):
        value={'uuid':'synthetic','name':'Demo','fields':{'customField1':'8u 00m'}}
        self.assertEqual(self.call({'ok':True,'data':value,'warnings':['certificate_untrusted']},'patch'),value)
        self.assertEqual(self.db.loxone_sync_status.count_documents({}),0)
    def test_real_auth_or_network_error_remains_error_even_after_certificate_fallback(self):
        for code in ('authentication','permissions','network','verification'):
            with self.subTest(code=code),self.assertRaises(SyncError) as error:
                self.call({'ok':False,'error':code,'warnings':['certificate_untrusted']})
            self.assertEqual(error.exception.code,code)
        self.assertTrue(self.service.transport_status(SERVER)['warnings'])
    def test_unknown_warning_details_are_never_exposed_or_persisted(self):
        result=self.call({'ok':True,'data':{},'warnings':['password=synthetic-private',{'secret':'synthetic-private'},'certificate_untrusted','certificate_untrusted']})
        self.assertEqual(len(result['transport_warnings']),1)
        text=json.dumps(result)+json.dumps(self.service.preview(remote=False),default=str)
        self.assertNotIn('synthetic-private',text)
    def test_inventory_does_not_clear_selected_server_warning(self):
        self.call({'ok':True,'data':{},'warnings':['certificate_expired']})
        self.call({'ok':True,'data':{'servers':[]},'warnings':[]},'miniservers',None)
        self.assertTrue(self.service.transport_status(SERVER)['warnings'])
    def test_different_server_is_isolated(self):
        self.call({'ok':True,'data':{},'warnings':['certificate_expired']},server={'slot':'2'})
        self.assertFalse(self.service.transport_status(SERVER)['warnings'])
    def test_transport_failure_does_not_clear_known_warning(self):
        self.call({'ok':True,'data':{},'warnings':['certificate_expired']})
        with self.assertRaises(SyncError):self.call({'ok':False,'error':'network','warnings':[]})
        self.assertTrue(self.service.transport_status(SERVER)['warnings'])
    def test_older_host_envelope_is_compatible_without_clearing_warning(self):
        self.call({'ok':True,'data':{},'warnings':['certificate_expired']})
        self.call({'ok':True,'data':{}})
        self.assertTrue(self.service.transport_status(SERVER)['warnings'])
    def test_diagnostic_storage_failure_does_not_fail_transport(self):
        with patch.object(self.db.loxone_sync_meta,'update_one',side_effect=RuntimeError('synthetic-private')):
            result=self.call({'ok':True,'data':{'safe':True},'warnings':['certificate_untrusted']})
        self.assertTrue(result['safe'])

if __name__=='__main__':unittest.main()
