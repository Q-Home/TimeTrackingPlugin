#!/usr/bin/env python3
"""Preserve private plugin state and apply application images during a ZIP update."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

RUNTIME_FILES = ('.env', 'backend/.env', 'docker-compose.yml', 'docker-compose.override.yml')
SERVICES = ('backend', 'mqtt-listener', 'webapp')


def paths(home, folder, archive):
    if not re.fullmatch(r'[A-Za-z0-9_-]+', folder):
        raise ValueError('Invalid plugin installation folder')
    home, archive = Path(home).resolve(), Path(archive).resolve()
    return {
        'bin': home / 'bin' / 'plugins' / folder,
        'config': home / 'config' / 'plugins' / folder,
        'data': home / 'data' / 'plugins' / folder,
        'state': archive / '.timetracking-state' / folder,
    }


def docker(args, cwd=None, capture=False):
    return subprocess.run(
        ['docker', *args], cwd=cwd, check=True, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    ).stdout


def private_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2), encoding='utf-8')
    path.chmod(0o600)


def backup(home, folder, archive):
    p = paths(home, folder, archive)
    state = p['state']
    if state.exists():
        raise ValueError('State backup already exists; refusing to overwrite it')
    state.mkdir(parents=True, mode=0o700)
    state.chmod(0o700)
    for name in RUNTIME_FILES:
        source = p['bin'] / name
        if source.is_file():
            target = state / 'runtime' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    for name in ('config', 'data'):
        if p[name].is_dir():
            shutil.copytree(p[name], state / name, symlinks=True)
    if (p['bin'] / 'logs').is_dir():
        shutil.copytree(p['bin'] / 'logs', state / 'logs', symlinks=True)
    # Inspect is read-only. Keep the snapshot private; never print environments.
    containers = []
    try:
        containers = json.loads(docker(['inspect', *SERVICES, 'mongodb'], capture=True))
    except (OSError, subprocess.CalledProcessError, ValueError):
        pass
    private_json(state / 'containers.json', containers)
    private_json(state / 'state.json', {'folder':folder, 'had_installation':p['bin'].is_dir()})
    print('<OK> Saved existing local configuration and plugin state before replacement.')


def environment_from_containers(containers):
    by_name = {c.get('Name','').lstrip('/'):c for c in containers}
    envs = {}
    for name, container in by_name.items():
        envs[name] = dict(item.split('=',1) for item in container.get('Config',{}).get('Env',[]) if '=' in item)
    values = {}
    for key in ('MONGO_URI','SECRET_KEY','JWT_SECRET_KEY','INTERNAL_API_KEY','INTERNAL_TRUSTED_SUBNETS','FLASK_DEBUG','DOCKER_ENV'):
        if key in envs.get('backend',{}):values[key] = envs['backend'][key]
    listener = envs.get('mqtt-listener',{})
    for key in ('MONGO_HOST','MONGO_PORT','MONGO_DB_NAME','MONGO_COLLECTION_NAME','MQTT_BROKER','MQTT_PORT','MQTT_TOPIC','MQTT_STATS_TOPIC','MQTT_PUB_TOPIC','MQTT_USERNAME','MQTT_PASSWORD','BACKEND_API','MQTT_LOG_PAYLOADS'):
        if key in listener:values[key] = listener[key]
    if 'URI' in envs.get('webapp',{}):values['WEBAPP_BACKEND_URI'] = envs['webapp']['URI']
    for name, port, key in (('backend','5000/tcp','BACKEND_HOST_PORT'),('webapp','80/tcp','WEBAPP_HOST_PORT')):
        mappings = by_name.get(name,{}).get('NetworkSettings',{}).get('Ports',{}).get(port) or []
        if mappings and mappings[0].get('HostPort'):values[key] = mappings[0]['HostPort']
    return values


def recover_environment(plugin_bin, containers):
    compose = plugin_bin / 'docker-compose.yml'
    env_file = plugin_bin / '.env'
    if env_file.exists() or not compose.is_file():return False
    required = set(re.findall(r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}', compose.read_text(encoding='utf-8')))
    if not required:return False  # Preserve literal-valued installations as-is.
    values = environment_from_containers(containers)
    missing = sorted(required - values.keys())
    if missing:
        raise ValueError('Private configuration is incomplete; set these keys in bin/.env: '+', '.join(missing))
    for value in values.values():
        if '\n' in value or '\r' in value:
            raise ValueError('Cannot safely migrate a multiline environment value; configure it privately')
    # Compose single quotes preserve dollar signs in passwords literally.
    lines = [key+"='"+value.replace("'", "\\'")+"'" for key,value in sorted(values.items())]
    fd = os.open(env_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as target:
        target.write('\n'.join(lines)+'\n')
    env_file.chmod(0o600)
    print('<OK> Recovered private Compose settings from the existing containers without displaying them.')
    return True


def restore(home, folder, archive):
    p = paths(home, folder, archive)
    state = p['state']
    metadata = json.loads((state/'state.json').read_text(encoding='utf-8'))
    if metadata.get('folder') != folder:raise ValueError('Backup belongs to a different plugin folder')
    for name in RUNTIME_FILES:
        source = state / 'runtime' / name
        if source.is_file():
            target = p['bin'] / name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
    for name in ('config','data'):
        if (state/name).is_dir():
            shutil.copytree(state/name,p[name],symlinks=True,dirs_exist_ok=True)
    if (state/'logs').is_dir():
        shutil.copytree(state/'logs',p['bin']/'logs',symlinks=True,dirs_exist_ok=True)
    containers = json.loads((state/'containers.json').read_text(encoding='utf-8'))
    recover_environment(p['bin'],containers)
    print('<OK> Restored existing local configuration and plugin state.')
    return p


def write_version(plugin_bin, version):
    webapp = plugin_bin / 'Webapp'
    digest = hashlib.sha256()
    for path in sorted(webapp.rglob('*')):
        if path.is_file() and not path.is_symlink() and path.suffix in {'.html','.js','.css','.conf'}:
            digest.update(path.relative_to(webapp).as_posix().encode()+b'\0'+path.read_bytes()+b'\0')
    value = {'plugin_version':version, 'frontend_sha256':digest.hexdigest(),
             'built_at':datetime.now(timezone.utc).isoformat()}
    (webapp/'version.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    return value


def deploy(plugin_bin, version):
    running = docker(['inspect','mongodb','--format','{{.State.Running}}'],capture=True)
    if running.strip() != 'true':
        raise ValueError('MongoDB is not running; configure/start the installation before applying application images')
    compose = ['compose']
    if (plugin_bin/'docker-compose.loxone.yml').is_file():
        compose += ['-f','docker-compose.yml']
        if (plugin_bin/'docker-compose.override.yml').is_file():
            compose += ['-f','docker-compose.override.yml']
        compose += ['-f','docker-compose.loxone.yml']
    docker([*compose,'config','--quiet'],cwd=plugin_bin)
    expected = write_version(plugin_bin,version)
    # Build first: a build failure must leave current containers running.
    docker([*compose,'build',*SERVICES],cwd=plugin_bin)
    # Never recreate MongoDB or remove its volumes as part of a GUI/plugin update.
    docker([*compose,'up','-d','--no-deps','--force-recreate',*SERVICES],cwd=plugin_bin)
    actual = json.loads(docker(['exec','webapp','cat','/usr/share/nginx/html/version.json'],capture=True))
    if actual != expected:
        raise ValueError('Application restart finished but the served frontend version does not match; inspect deployment logs')
    print('<OK> Applied plugin '+version+' and verified the frontend inside the running webapp container.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('backup','finish'))
    parser.add_argument('--home',required=True)
    parser.add_argument('--folder',required=True)
    parser.add_argument('--archive',required=True)
    parser.add_argument('--version',default='unknown')
    args = parser.parse_args()
    try:
        if args.phase=='backup':backup(args.home,args.folder,args.archive)
        else:
            p = restore(args.home,args.folder,args.archive)
            host_installer = p['bin']/'host/install_adapter.py'
            if host_installer.is_file():
                try:
                    subprocess.run([sys.executable,str(host_installer),args.home,args.folder],check=True)
                except (OSError, subprocess.CalledProcessError):
                    print('<WARNING> Loxone host adapter unavailable. Timekeeping can run; synchronization remains unavailable until host setup is repaired.')
            deploy(p['bin'],args.version)
        return 0
    except Exception as exc:
        # Command exceptions name the failed command, not captured secret output.
        print('<ERROR> TimeTracking update failed: '+str(exc),file=sys.stderr)
        if args.phase=='finish':
            print('<WARNING> Source files were installed, but activation was not confirmed. Check the plugin installation log; do not remove database volumes.',file=sys.stderr)
        return 2 if args.phase=='backup' else 1


if __name__=='__main__':
    raise SystemExit(main())
