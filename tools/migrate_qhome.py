#!/usr/bin/env python3
"""One-time, locked migration of the existing LoxBerry plugin identity."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

NAME = 'timetrackingplugin'
AUTHOR = 'Q-Home'
EMAIL = 'info@q-home.be'
FEED = 'https://raw.githubusercontent.com/Q-Home/TimeTrackingPlugin/updates/release.cfg'


def identity(record):
    text = ''.join(record[k] for k in ('author_name', 'author_email', 'name', 'folder'))
    return hashlib.md5(text.encode('utf-8')).hexdigest()


def converted(database):
    result = deepcopy(database)
    plugins = result['plugins']
    matches = [(key, item) for key, item in plugins.items()
               if item.get('name') == NAME and item.get('folder') == NAME]
    if len(matches) != 1:
        raise ValueError('Expected exactly one existing TimeTrackingPlugin installation; nothing changed.')
    old_key, record = matches[0]
    if record.get('md5') != old_key or identity(record) != old_key:
        raise ValueError('Existing plugin identity is inconsistent; nothing changed.')
    record.update(author_name=AUTHOR, author_email=EMAIL, maintainer_name=AUTHOR,
                  maintainer_email=EMAIL, autoupdate=3, releasecfg=FEED, prereleasecfg=FEED)
    new_key = identity(record)
    if new_key != old_key and new_key in plugins:
        raise ValueError('A Q-Home plugin identity already exists; nothing changed.')
    # Preserve the real folders, version, installation dates and all other fields.
    del plugins[old_key]
    record['md5'] = new_key
    plugins[new_key] = record
    return result


def atomic_bytes(path, content, reference):
    fd, temporary = tempfile.mkstemp(prefix='.qhome-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, reference.st_mode & 0o777)
        if os.name == 'posix':
            os.chown(temporary, reference.st_uid, reference.st_gid)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def migrate(home):
    path = Path(home) / 'data/system/plugindatabase.json'
    original = path.read_bytes()
    content = (json.dumps(converted(json.loads(original)), indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    reference = path.stat()
    shadow = path.with_name(path.name + '-')
    old_shadow = shadow.read_bytes() if shadow.exists() else None
    shadow_reference = shadow.stat() if shadow.exists() else reference
    backup = Path(home) / 'data/plugins' / NAME / 'identity-backups'
    backup.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup.chmod(0o700)
    # Keep recovery data private; do not print the database or previous author.
    fd, saved = tempfile.mkstemp(prefix=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-'), suffix='.json', dir=backup)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(original)
    os.chmod(saved, 0o600)
    try:
        atomic_bytes(shadow, content, shadow_reference)
        atomic_bytes(path, content, reference)
    except Exception:
        atomic_bytes(path, original, reference)
        if old_shadow is None:
            if shadow.exists(): shadow.unlink()
        else:
            atomic_bytes(shadow, old_shadow, shadow_reference)
        raise
    print('Q-Home identity and Releases updates enabled. Existing version, folders and application data preserved.')


def main():
    if os.name != 'posix' or os.geteuid() != 0:
        raise ValueError('Run this migration on the Qbox with sudo python3.')
    home = os.environ.get('LBHOMEDIR', '/opt/loxberry')
    if sys.argv[1:] == ['--locked']:
        migrate(home)
        return
    if sys.argv[1:]:
        raise ValueError('Unexpected arguments.')
    # Use LoxBerry's own installation lock, including its system-update checks.
    perl = r'''use strict; use warnings; use LoxBerry::System;
my $state=LoxBerry::System::lock(lockfile=>'plugininstall',wait=>0);
die "An installation or system update is active; try later.\n" if $state;
my $rc=system('python3',$ARGV[0],'--locked');
LoxBerry::System::unlock(lockfile=>'plugininstall');
exit($rc == -1 || ($rc & 127) ? 1 : $rc >> 8);
'''
    subprocess.run(['perl', '-I'+str(Path(home)/'libs/perllib'), '-e', perl, str(Path(__file__).resolve())], check=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('Migration stopped: '+str(exc), file=sys.stderr)
        sys.exit(1)
