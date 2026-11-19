#!/usr/bin/env python3
"""Called by the root ZIP lifecycle; never copies Miniserver configuration."""
import os
from pathlib import Path,PurePosixPath
import re
import subprocess
import sys

CRON_NAME='timetrackingplugin-loxone-sync'
CRON_MARKER='# Managed by TimeTrackingPlugin: Loxone synchronization'

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
