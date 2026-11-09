"""ZIP lifecycle tests use temporary folders and a fake Docker command only."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('plugin_lifecycle',ROOT/'bin/plugin_lifecycle.py')
lifecycle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lifecycle)


class PluginUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home,self.archive = self.root/'home',self.root/'archive'
        self.archive.mkdir()
        self.folder = 'timetrackingplugin'
        self.bin = self.home/'bin/plugins'/self.folder
        self.bin.mkdir(parents=True)
        (self.bin/'Webapp').mkdir()
        (self.bin/'Webapp/index.html').write_text('new GUI',encoding='utf-8')
        self.containers = [
            {'Name':'/backend','Config':{'Env':['MONGO_URI=mongodb://mongodb/timetracking','SECRET_KEY=synthetic','JWT_SECRET_KEY=synthetic-jwt']},'NetworkSettings':{'Ports':{'5000/tcp':[{'HostPort':'5100'}]}}},
            {'Name':'/mqtt-listener','Config':{'Env':["MQTT_PASSWORD=synthetic$quote'password",'MQTT_BROKER=192.0.2.1']}},
            {'Name':'/webapp','Config':{'Env':['URI=http://example.invalid']},'NetworkSettings':{'Ports':{'80/tcp':[{'HostPort':'8088'}]}}},
        ]

    def backup(self):
        with patch.object(lifecycle,'docker',return_value=json.dumps(self.containers)),redirect_stdout(io.StringIO()):
            lifecycle.backup(self.home,self.folder,self.archive)

    def restore(self):
        with redirect_stdout(io.StringIO()):
            return lifecycle.restore(self.home,self.folder,self.archive)

    def test_literal_compose_private_files_and_settings_survive_replacement(self):
        original='services:\n  backend:\n    environment:\n      SECRET_KEY: synthetic-local\n'
        (self.bin/'docker-compose.yml').write_text(original,encoding='utf-8')
        (self.bin/'.env').write_text('PRIVATE=synthetic-only\n',encoding='utf-8')
        config = self.home/'config/plugins'/self.folder
        data = self.home/'data/plugins'/self.folder
        for directory in (config,data):directory.mkdir(parents=True)
        (config/'custom.json').write_text('{"local":true}',encoding='utf-8')
        (data/'settings.json').write_text('{"backend_url":"local"}',encoding='utf-8')
        self.backup()
        shutil.rmtree(self.bin)
        shutil.rmtree(config)
        shutil.rmtree(data)
        self.bin.mkdir(parents=True)
        (self.bin/'docker-compose.yml').write_text('new defaults',encoding='utf-8')
        self.restore()
        self.assertEqual((self.bin/'docker-compose.yml').read_text(),original)
        self.assertIn('synthetic-only',(self.bin/'.env').read_text())
        self.assertEqual(json.loads((config/'custom.json').read_text()),{'local':True})
        self.assertEqual(json.loads((data/'settings.json').read_text()),{'backend_url':'local'})

    def test_parameterized_compose_can_recover_live_values_without_printing_them(self):
        (self.bin/'docker-compose.yml').write_text('${MQTT_PASSWORD}\n${MONGO_URI}\n${MQTT_BROKER}',encoding='utf-8')
        self.backup()
        output = io.StringIO()
        with redirect_stdout(output):lifecycle.restore(self.home,self.folder,self.archive)
        env=(self.bin/'.env').read_text(encoding='utf-8')
        self.assertIn("MQTT_PASSWORD='synthetic$quote\\'password'",env)
        self.assertIn("BACKEND_HOST_PORT='5100'",env)
        self.assertIn("WEBAPP_HOST_PORT='8088'",env)
        self.assertNotIn('synthetic$quote',output.getvalue())
        from dotenv import dotenv_values
        self.assertEqual(dotenv_values(self.bin/'.env')['MQTT_PASSWORD'],"synthetic$quote'password")

    def test_existing_env_is_never_replaced_from_container_values(self):
        (self.bin/'docker-compose.yml').write_text('${MQTT_PASSWORD}',encoding='utf-8')
        (self.bin/'.env').write_text('MQTT_PASSWORD=local-only',encoding='utf-8')
        self.backup();self.restore()
        self.assertEqual((self.bin/'.env').read_text(),'MQTT_PASSWORD=local-only')

    def test_missing_required_configuration_fails_before_activation(self):
        (self.bin/'docker-compose.yml').write_text('${NEW_REQUIRED_SETTING}',encoding='utf-8')
        self.backup()
        with self.assertRaisesRegex(ValueError,'NEW_REQUIRED_SETTING'):self.restore()
        self.assertFalse((self.bin/'.env').exists())

    def test_invalid_plugin_folder_is_rejected(self):
        with self.assertRaises(ValueError):lifecycle.paths(self.home,'../other',self.archive)

    def test_existing_backup_is_not_silently_overwritten(self):
        self.backup()
        with self.assertRaisesRegex(ValueError,'already exists'):self.backup()

    def test_failed_build_does_not_recreate_containers(self):
        calls=[]
        def fake(args,**kwargs):
            calls.append(args)
            if args[0]=='inspect':return 'true\n'
            if args[:2]==['compose','build']:raise subprocess.CalledProcessError(1,args)
            return ''
        with patch.object(lifecycle,'docker',side_effect=fake):
            with self.assertRaises(subprocess.CalledProcessError):lifecycle.deploy(self.bin,'1.0.1')
        self.assertFalse(any(c[:2]==['compose','up'] for c in calls))

    def test_successful_activation_rebuilds_apps_and_checks_served_version(self):
        calls=[]
        def fake(args,**kwargs):
            calls.append(args)
            if args[0]=='inspect':return 'true\n'
            if args[:2]==['exec','webapp']:return (self.bin/'Webapp/version.json').read_text()
            return ''
        with patch.object(lifecycle,'docker',side_effect=fake),redirect_stdout(io.StringIO()):
            lifecycle.deploy(self.bin,'1.0.1')
        build=next(c for c in calls if c[:2]==['compose','build'])
        up=next(c for c in calls if c[:2]==['compose','up'])
        self.assertEqual(build[2:],['backend','mqtt-listener','webapp'])
        self.assertIn('--no-deps',up)
        self.assertNotIn('mongodb',up)
        self.assertFalse(any(c[:2]==['compose','down'] for c in calls))
        marker=json.loads((self.bin/'Webapp/version.json').read_text())
        self.assertEqual(marker['plugin_version'],'1.0.1')
        self.assertEqual(len(marker['frontend_sha256']),64)

    def test_stale_container_is_not_reported_as_success(self):
        def fake(args,**kwargs):
            if args[0]=='inspect':return 'true\n'
            if args[:2]==['exec','webapp']:return '{}'
            return ''
        with patch.object(lifecycle,'docker',side_effect=fake):
            with self.assertRaisesRegex(ValueError,'does not match'):lifecycle.deploy(self.bin,'1.0.1')

    def test_stopped_database_prevents_build_or_recreate(self):
        with patch.object(lifecycle,'docker',return_value='false\n') as fake:
            with self.assertRaisesRegex(ValueError,'MongoDB is not running'):lifecycle.deploy(self.bin,'1.0.1')
        self.assertEqual(fake.call_count,1)

    def test_sync_overlay_combines_with_preserved_local_compose(self):
        (self.bin/'docker-compose.yml').write_text('local compose',encoding='utf-8')
        (self.bin/'docker-compose.override.yml').write_text('local overrides',encoding='utf-8')
        (self.bin/'docker-compose.loxone.yml').write_text('socket-only overlay',encoding='utf-8')
        calls=[]
        def fake(args,**kwargs):
            calls.append(args)
            if args[0]=='inspect':return 'true'
            if args[:2]==['exec','webapp']:return (self.bin/'Webapp/version.json').read_text()
            return ''
        with patch.object(lifecycle,'docker',side_effect=fake),redirect_stdout(io.StringIO()):lifecycle.deploy(self.bin,'1.2.0')
        build=next(c for c in calls if 'build' in c)
        self.assertEqual(build[:7],['compose','-f','docker-compose.yml','-f','docker-compose.override.yml','-f','docker-compose.loxone.yml'])
        self.assertNotIn('mongodb',build)
        self.assertEqual((self.bin/'docker-compose.yml').read_text(),'local compose')

    @unittest.skipIf(os.name=='nt','Shell-hook subprocess smoke test runs on the Linux CI runner')
    def test_zip_hooks_preserve_state_and_activate_the_new_frontend(self):
        # Exercise the real shell hooks and Python CLI; only the Docker binary is fake.
        (self.bin/'docker-compose.yml').write_text('services: {}\n# original-local-config\n',encoding='utf-8')
        (self.bin/'.env').write_text('PRIVATE=synthetic-hook-only\n',encoding='utf-8')
        data=self.home/'data/plugins'/self.folder
        data.mkdir(parents=True)
        (data/'settings.json').write_text('{"local":true}',encoding='utf-8')
        (self.archive/'bin').mkdir()
        shutil.copy2(ROOT/'bin/plugin_lifecycle.py',self.archive/'bin/plugin_lifecycle.py')
        fake_bin=self.root/'fake-bin';fake_bin.mkdir()
        fake_impl=self.root/'fake_docker.py'
        fake_impl.write_text('''import json,os,pathlib,sys
args=sys.argv[1:]
with open(os.environ['FAKE_CALLS'],'a',encoding='utf-8') as out:out.write(json.dumps(args)+'\\n')
if args==['inspect','backend','mqtt-listener','webapp','mongodb']:print('[]')
elif args[:2]==['inspect','mongodb']:print('true')
elif args[:2]==['exec','webapp']:print(pathlib.Path(os.environ['FAKE_PLUGIN_BIN'],'Webapp','version.json').read_text())
''',encoding='utf-8')
        fake_docker=fake_bin/'docker'
        fake_docker.write_text('#!/bin/sh\nexec "$FAKE_PYTHON" "$FAKE_IMPL" "$@"\n',encoding='utf-8')
        fake_docker.chmod(0o755)
        env=dict(os.environ,LBHOMEDIR=str(self.home),FAKE_PYTHON=sys.executable,
                 FAKE_IMPL=str(fake_impl),FAKE_CALLS=str(self.root/'docker-calls.jsonl'),
                 FAKE_PLUGIN_BIN=str(self.bin))
        env['PATH']=str(fake_bin)+os.pathsep+str(Path(sys.executable).parent)+os.pathsep+env['PATH']
        args=['temporary',self.folder,self.folder,'1.0.1',str(self.home),str(self.archive)]
        before=subprocess.run(['bash',str(ROOT/'preroot.sh'),*args],env=env,capture_output=True,text=True)
        self.assertEqual(before.returncode,0,before.stdout+before.stderr)
        shutil.rmtree(self.bin);shutil.rmtree(data)
        (self.bin/'Webapp').mkdir(parents=True)
        (self.bin/'Webapp/index.html').write_text('updated GUI from new ZIP',encoding='utf-8')
        (self.bin/'docker-compose.yml').write_text('new-package-defaults',encoding='utf-8')
        after=subprocess.run(['bash',str(ROOT/'postroot.sh'),*args],env=env,capture_output=True,text=True)
        self.assertEqual(after.returncode,0,after.stdout+after.stderr)
        self.assertIn('verified the frontend',after.stdout)
        self.assertNotIn('synthetic-hook-only',before.stdout+after.stdout)
        self.assertIn('original-local-config',(self.bin/'docker-compose.yml').read_text())
        self.assertEqual(json.loads((data/'settings.json').read_text()),{'local':True})
        self.assertEqual((self.bin/'Webapp/index.html').read_text(),'updated GUI from new ZIP')
        calls=[json.loads(line) for line in (self.root/'docker-calls.jsonl').read_text().splitlines()]
        up=next(c for c in calls if c[:2]==['compose','up'])
        self.assertIn('--no-deps',up)
        self.assertNotIn('mongodb',up)


if __name__=='__main__':unittest.main()
