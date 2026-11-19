"""Host scheduler files use temporary directories; no live cron or Docker."""
import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('scheduler_installer',ROOT/'bin/host/install_adapter.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.cron=Path(self.temp.name)/'cron.d';self.cron.mkdir()
    def write(self):return installer.write_scheduler('/opt/loxberry','timetrackingplugin',self.cron)
    def test_missing_task_is_installed_with_final_newline_and_no_credentials(self):
        path=self.write();text=path.read_text(encoding='utf-8')
        self.assertIn('* * * * * loxberry ',text)
        self.assertIn('mkdir -p /opt/loxberry/log/plugins/timetrackingplugin && flock',text)
        self.assertIn('/run/timetracking-loxone/sync-worker.lock',text)
        self.assertIn('docker exec backend python /app/scripts/loxone_sync.py',text)
        self.assertTrue(text.endswith('\n'));self.assertNotIn('password',text.lower())
        self.assertEqual(len(list(self.cron.iterdir())),1)
        if os.name=='posix':self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o644)
    def test_repeated_install_has_one_task_and_retains_unrelated_jobs(self):
        other=self.cron/'other-plugin';other.write_text('0 1 * * * root /bin/true\n')
        self.write();self.write()
        self.assertEqual(len(list(self.cron.iterdir())),2)
        self.assertEqual(other.read_text(),'0 1 * * * root /bin/true\n')
    def test_existing_managed_task_is_reused_without_duplicate(self):
        other=self.cron/'loxberry-managed';content='* * * * * loxberry docker exec backend python /app/scripts/loxone_sync.py\n'
        other.write_text(content)
        self.assertEqual(self.write(),other)
        self.assertFalse((self.cron/installer.CRON_NAME).exists());self.assertEqual(other.read_text(),content)
    def test_only_our_generated_duplicate_is_removed(self):
        ours=self.write();other=self.cron/'legacy';other.write_text('* * * * * loxberry docker exec backend python /app/scripts/loxone_sync.py\n')
        self.assertEqual(self.write(),other);self.assertFalse(ours.exists())
    def test_comments_do_not_count_as_a_running_task(self):
        (self.cron/'notes').write_text('# loxone_sync.py is not installed\n')
        self.assertEqual(self.write().name,installer.CRON_NAME)
    def test_ignored_backup_and_temporary_files_do_not_mask_missing_job(self):
        for name in ('.temporary','backup.bak'):
            (self.cron/name).write_text('* * * * * loxberry docker exec backend python /app/scripts/loxone_sync.py\n')
        self.assertEqual(self.write().name,installer.CRON_NAME)
    def test_custom_content_at_owned_name_is_preserved(self):
        ours=self.cron/installer.CRON_NAME;ours.write_text('# custom administrator task\n')
        with self.assertRaises(ValueError):self.write()
        self.assertEqual(ours.read_text(),'# custom administrator task\n')
    def test_shell_paths_are_validated_before_building_cron(self):
        for home,folder in [('/opt/loxberry;bad','timetrackingplugin'),('/opt/loxberry','../other'),('/opt/loxberry','a b')]:
            with self.assertRaises(ValueError):installer.cron_content(home,folder)
    @unittest.skipUnless(os.name=='posix','Root installer integration runs on Linux')
    def test_root_install_invokes_scheduler_after_host_service_start(self):
        from types import SimpleNamespace
        with patch.object(installer.os,'geteuid',return_value=0),patch('pwd.getpwnam',return_value=SimpleNamespace(pw_uid=1000,pw_gid=1000)),patch.object(installer.subprocess,'run') as run,patch.object(installer.Path,'write_text'),patch.object(installer.Path,'mkdir'),patch.object(installer.os,'chown'),patch.object(installer,'write_scheduler',return_value=Path('/etc/cron.d/test')) as write:
            installer.install('/opt/loxberry','timetrackingplugin')
            write.assert_called_once_with('/opt/loxberry','timetrackingplugin')
            self.assertTrue(any(c.args[0]==['systemctl','restart','timetracking-loxone.service'] for c in run.call_args_list))

if __name__=='__main__':unittest.main()
