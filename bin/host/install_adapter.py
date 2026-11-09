#!/usr/bin/env python3
"""Called by the root ZIP lifecycle; never copies Miniserver configuration."""
import os
from pathlib import Path
import re
import subprocess
import sys


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


if __name__=='__main__':install(sys.argv[1],sys.argv[2])
