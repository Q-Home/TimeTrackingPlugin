"""Host scheduler files use temporary directories; no live cron or Docker."""
import importlib.util
import os
from pathlib import Path
import stat
import shutil
import subprocess
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
    def test_auto_close_timer_has_boot_nightly_and_retry_triggers(self):
        units=installer.auto_close_units('/opt/loxberry','timetrackingplugin')
        service=units['timetracking-auto-close.service'];timer=units['timetracking-auto-close.timer']
        self.assertIn('Type=oneshot',service);self.assertIn('User=loxberry',service)
        self.assertIn('--completed-days --catch-up-all',service)
        self.assertNotIn('/run/lock',service)
        self.assertIn('OnCalendar=*-*-* 00:05:00',timer)
        self.assertIn('OnBootSec=2min',timer);self.assertIn('Persistent=true',timer)
    def test_systemd_timer_calendar_expressions_are_valid(self):
        binary=shutil.which('systemd-analyze')
        if not binary:self.skipTest('Calendar validation requires Linux systemd-analyze')
        timer=installer.auto_close_units('/opt/loxberry','timetrackingplugin')['timetracking-auto-close.timer']
        for line in timer.splitlines():
            if line.startswith('OnCalendar='):
                result=subprocess.run([binary,'calendar',line.split('=',1)[1]],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
    def test_auto_close_units_are_repeatable_and_custom_unit_is_preserved(self):
        units=Path(self.temp.name)/'units'
        installer.write_auto_close('/opt/loxberry','timetrackingplugin',units)
        installer.write_auto_close('/opt/loxberry','timetrackingplugin',units)
        self.assertEqual(len(list(units.iterdir())),2)
        custom=units/'timetracking-auto-close.timer';custom.write_text('# local administrator unit')
        with self.assertRaises(ValueError):installer.write_auto_close('/opt/loxberry','timetrackingplugin',units)
        self.assertEqual(custom.read_text(),'# local administrator unit')
    def test_old_plugin_cron_is_retired_but_other_lines_are_preserved(self):
        home=Path(self.temp.name)/'home';legacy=home/'system/cron/cron.d/timetrackingplugin';legacy.parent.mkdir(parents=True)
        original='5 0 * * * loxberry flock -n /run/lock/timetracking-auto-close.lock docker exec backend python /app/scripts/auto_stop_missing_badges.py --completed-days\n0 4 * * * root /bin/true\n'
        legacy.write_text(original)
        with patch.object(installer,'cron_content',return_value='validated'):
            installer.retire_legacy_auto_close(str(home),'timetrackingplugin')
        self.assertNotIn('docker exec',legacy.read_text());self.assertIn('0 4 * * * root /bin/true',legacy.read_text())
        self.assertEqual(legacy.with_name(legacy.name+'.before-auto-close-timer').read_text(),original)
        with patch.object(installer,'cron_content',return_value='validated'):
            installer.retire_legacy_auto_close(str(home),'timetrackingplugin')
        self.assertIn('0 4 * * * root /bin/true',legacy.read_text())
    def test_timer_enable_failure_does_not_disable_old_cron(self):
        with patch.object(installer,'write_auto_close'),patch.object(installer.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['systemctl'])),patch.object(installer,'retire_legacy_auto_close') as retire:
            with self.assertRaises(subprocess.CalledProcessError):installer.install_auto_close('/opt/loxberry','timetrackingplugin')
            retire.assert_not_called()
    @unittest.skipUnless(os.name=='posix','Root installer integration runs on Linux')
    def test_root_install_invokes_scheduler_after_host_service_start(self):
        from types import SimpleNamespace
        with patch.object(installer.os,'geteuid',return_value=0),patch('pwd.getpwnam',return_value=SimpleNamespace(pw_uid=1000,pw_gid=1000)),patch.object(installer.subprocess,'run') as run,patch.object(installer.Path,'write_text'),patch.object(installer.Path,'mkdir'),patch.object(installer.os,'chown'),patch.object(installer,'write_scheduler',return_value=Path('/etc/cron.d/test')) as write,patch.object(installer,'install_auto_close') as auto_close:
            installer.install('/opt/loxberry','timetrackingplugin')
            write.assert_called_once_with('/opt/loxberry','timetrackingplugin')
            auto_close.assert_called_once_with('/opt/loxberry','timetrackingplugin')
            self.assertTrue(any(c.args[0]==['systemctl','restart','timetracking-loxone.service'] for c in run.call_args_list))

if __name__=='__main__':unittest.main()
