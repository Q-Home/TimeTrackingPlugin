#!/usr/bin/env python3
"""Called by the root ZIP lifecycle; never copies Miniserver configuration."""
import os
from pathlib import Path,PurePosixPath
import re
import subprocess
import sys

CRON_NAME='timetrackingplugin-loxone-sync'
CRON_MARKER='# Managed by TimeTrackingPlugin: Loxone synchronization'
AUTO_CLOSE_MARKER='# Managed by TimeTrackingPlugin: automatic STOP'


def auto_close_units(home,folder):
    cron_content(home,folder)  # Validate every interpolated shell path.
    logdir=PurePosixPath(str(home))/'log/plugins'/folder
    service=f'''{AUTO_CLOSE_MARKER}
[Unit]
Description=TimeTracking forgotten-session automatic STOP
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
User=loxberry
Group=loxberry
TimeoutStartSec=300
ExecStart=/bin/sh -c 'mkdir -p {logdir} && exec /usr/bin/docker exec backend python /app/scripts/auto_stop_missing_badges.py --completed-days --catch-up-all >> {logdir}/auto_stop_missing_badges.log 2>&1'
'''
    timer=f'''{AUTO_CLOSE_MARKER}
[Unit]
Description=TimeTracking nightly automatic STOP with catch-up

[Timer]
OnCalendar=*-*-* 00:05:00
OnCalendar=*-*-* *:00/10:00
OnBootSec=2min
Persistent=true
Unit=timetracking-auto-close.service

[Install]
WantedBy=timers.target
'''
    return {'timetracking-auto-close.service':service,'timetracking-auto-close.timer':timer}


def write_auto_close(home,folder,systemd_dir=Path('/etc/systemd/system')):
    units=auto_close_units(home,folder)
    systemd_dir=Path(systemd_dir)
    # Validate all reserved targets before changing anything.
    for name in units:
        target=systemd_dir/name
        if target.exists() and AUTO_CLOSE_MARKER not in target.read_text(encoding='utf-8'):
            raise ValueError('Automatic STOP unit has custom content; preserve and inspect it')
    systemd_dir.mkdir(parents=True,exist_ok=True)
    for name,content in units.items():
        target=systemd_dir/name;temporary=target.with_name('.'+name+'.tmp')
        temporary.write_text(content,encoding='utf-8');temporary.chmod(0o644);temporary.replace(target)


def retire_legacy_auto_close(home,folder):
    cron_content(home,folder)
    legacy=Path(home)/'system/cron/cron.d'/folder
    if not legacy.is_file():return
    original=legacy.read_text(encoding='utf-8')
    lines=[]
    for line in original.splitlines(keepends=True):
        if not line.lstrip().startswith('#') and re.search(r'\bdocker exec backend python /app/scripts/auto_stop_missing_badges\.py(?:\s|$)',line):
            lines.append('# Replaced by timetracking-auto-close.timer\n')
        else:lines.append(line)
    replacement=''.join(lines)
    if replacement!=original:
        backup=legacy.with_name(legacy.name+'.before-auto-close-timer')
        if not backup.exists():backup.write_text(original,encoding='utf-8')
        legacy.write_text(replacement,encoding='utf-8')


def install_auto_close(home,folder):
    write_auto_close(home,folder)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now','timetracking-auto-close.timer'],check=True)
    # Disable only our old packaged command after the replacement is active.
    retire_legacy_auto_close(home,folder)
    print('<OK> Automatic STOP timer enabled: nightly, boot and ten-minute catch-up.')

def cron_content(home,folder):
    if not re.fullmatch(r'[A-Za-z0-9_/-]+',str(home)) or not re.fullmatch(r'[A-Za-z0-9_-]+',folder):
        raise ValueError('Invalid installation path')
    logdir=PurePosixPath(str(home))/'log/plugins'/folder
    return f'''{CRON_MARKER}
MAILTO=""
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
* * * * * loxberry mkdir -p {logdir} && flock -n /run/timetracking-loxone/sync-worker.lock docker exec backend python /app/scripts/loxone_sync.py >> {logdir}/loxone_sync.log 2>&1
'''

def write_scheduler(home,folder,cron_dir=Path('/etc/cron.d')):
    content=cron_content(home,folder)
    cron_dir=Path(cron_dir);cron_dir.mkdir(parents=True,exist_ok=True)
    target=cron_dir/CRON_NAME
    if target.exists() and CRON_MARKER not in target.read_text(encoding='utf-8'):
        raise ValueError('Scheduler file has custom content; preserve it and inspect host configuration')
    for other in cron_dir.iterdir():
        if other==target or not other.is_file() or not re.fullmatch(r'[A-Za-z0-9_-]+',other.name):continue
        text=other.read_text(encoding='utf-8',errors='replace')
        if any(not line.lstrip().startswith('#') and re.match(r'^\s*(?:\S+\s+){5}(?:loxberry|root)\s+.*\bloxone_sync\.py(?:\s|$)',line) for line in text.splitlines()):
            if target.exists():target.unlink()  # Only our positively identified generated file.
            return other
    temporary=target.with_name('.'+CRON_NAME+'.tmp')
    temporary.write_text(content,encoding='utf-8');temporary.chmod(0o644)
    temporary.replace(target)
    return target


def unit(home,folder):
    if not re.fullmatch(r'[A-Za-z0-9_/-]+',str(home)) or not re.fullmatch(r'[A-Za-z0-9_-]+',folder):
        raise ValueError('Invalid installation path')
    script=Path(home)/'bin/plugins'/folder/'host/bridge_daemon.py'
    return f'''[Unit]
Description=TimeTracking private LoxBerry Miniserver adapter
After=network.target

[Service]
Type=simple
User=loxberry
Group=loxberry
Environment=LBHOMEDIR={home}
ExecStart=/usr/bin/python3 {script}
RuntimeDirectory=timetracking-loxone
RuntimeDirectoryMode=0700
RuntimeDirectoryPreserve=yes
UMask=0077
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/run/timetracking-loxone /dev/shm
StandardOutput=null
StandardError=null

[Install]
WantedBy=multi-user.target
'''


def install(home,folder):
    if os.name!='posix' or os.geteuid()!=0:raise ValueError('Root host installation required')
    # Independent of the Miniserver bridge and its successful startup.
    install_auto_close(home,folder)
    Path('/etc/systemd/system/timetracking-loxone.service').write_text(unit(home,folder),encoding='utf-8')
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','timetracking-loxone.service'],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['systemctl','restart','timetracking-loxone.service'],check=True)
    import pwd
    account=pwd.getpwnam('loxberry')
    logdir=Path(home)/'log/plugins'/folder
    logdir.mkdir(parents=True,exist_ok=True)
    os.chown(logdir,account.pw_uid,account.pw_gid)
    scheduler=write_scheduler(home,folder)
    print('<OK> Loxone synchronization task installed or verified: '+str(scheduler))


if __name__=='__main__':install(sys.argv[1],sys.argv[2])
