import importlib.util
import json
from pathlib import Path
import shutil
import socket
import socketserver
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class HostTests(unittest.TestCase):
    def test_service_has_no_network_listener_or_credentials(self):
        module=load('sync_host_install','bin/host/install_adapter.py')
        unit=module.unit('/opt/loxberry','timetrackingplugin')
        self.assertIn('User=loxberry',unit);self.assertIn('RuntimeDirectoryMode=0700',unit)
        self.assertIn('RuntimeDirectoryPreserve=yes',unit)
        self.assertNotIn('password',unit.lower());self.assertNotIn('EnvironmentFile',unit)
        with self.assertRaises(ValueError):module.unit('/opt/loxberry','../escape')
    def test_mount_is_only_the_backend_socket_directory(self):
        text=(ROOT/'bin/docker-compose.loxone.yml').read_text()
        self.assertIn('/run/timetracking-loxone:/run/timetracking-loxone:ro',text)
        self.assertNotIn('webapp:',text);self.assertNotIn('/config',text)
    @unittest.skipUnless(shutil.which('php'),'PHP CLI adapter fixtures run in Linux CI')
    def test_real_php_adapter_against_synthetic_transport(self):
        result=subprocess.run(['php',str(ROOT/'tests/loxone_adapter_test.php')],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('assertions passed',result.stdout)
        self.assertNotIn('SYNTHETIC_PRIVATE',result.stdout+result.stderr)
    @unittest.skipUnless(hasattr(socket,'AF_UNIX'),'Unix socket test runs on Linux')
    def test_private_rpc_reads_one_bounded_request_without_shell_or_stderr(self):
        module=load('sync_host_daemon','bin/host/bridge_daemon.py')
        from app.loxone_sync.bridge import Bridge
        with tempfile.TemporaryDirectory() as temp:
            path=str(Path(temp)/'adapter.sock')
            with socketserver.UnixStreamServer(path,module.Handler) as server:
                with patch.object(module.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'{"ok":true,"data":{"safe":true}}\n')) as process:
                    thread=threading.Thread(target=server.handle_request);thread.start()
                    self.assertEqual(Bridge(path).call('miniservers'),{'safe':True});thread.join(timeout=5)
                    args,kwargs=process.call_args
                    self.assertIsInstance(args[0],list);self.assertNotIn('shell',kwargs)
                    self.assertEqual(kwargs['stderr'],subprocess.DEVNULL)
                    self.assertLessEqual(kwargs['timeout'],38)


if __name__=='__main__':unittest.main()
