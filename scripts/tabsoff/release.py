#!/usr/bin/env python3
"""Root-owned operator helper. Install manually; never execute PR-supplied code as root."""
import datetime
from contextlib import closing
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time

IMAGE = re.compile(r"ghcr\.io/tabsoff/opentodo@sha256:[0-9a-f]{64}\Z")
REVISION = re.compile(r"[0-9a-f]{40}\Z")
STATE = Path('/var/lib/opentodo-release')
BACKUPS = Path('/var/backups/opentodo-releases')
PROD = Path('/opt/opentodo')
TEST = Path('/opt/opentodo-test')
SNIPPET = Path('/etc/caddy/opentodo-release.caddy')


def run(*args, input=None, env=None, timeout=180):
    result = subprocess.run(args, input=input, text=True, capture_output=True,
                            timeout=timeout, env=env)
    if result.returncode:
        # Do not include credentials or application content in CI logs.
        raise RuntimeError(f'{args[0]} failed (exit {result.returncode}); inspect server privately')
    return result.stdout.strip()


def write_json(path, obj):
    temp = path.with_suffix(path.suffix + '.new')
    temp.write_text(json.dumps(obj, indent=2) + '\n')
    temp.chmod(0o600)
    temp.replace(path)


def read_json(path):
    return json.loads(path.read_text())


def validate(request):
    if not isinstance(request, dict) or set(request) - {'action', 'image', 'revision', 'registry_user', 'registry_token'}:
        raise ValueError('invalid request fields')
    action = request.get('action')
    if action not in ('stage', 'promote', 'rollback', 'status'):
        raise ValueError('invalid action')
    if action in ('stage', 'promote'):
        if not isinstance(request.get('image'), str) or not IMAGE.fullmatch(request['image']):
            raise ValueError('only this fork image by digest is allowed')
        if not isinstance(request.get('revision'), str) or not REVISION.fullmatch(request['revision']):
            raise ValueError('full commit revision required')
    allowed = {'action'}
    if action in ('stage', 'promote'):
        allowed |= {'image', 'revision'}
    if action == 'stage':
        allowed |= {'registry_user', 'registry_token'}
        user, token = request.get('registry_user', ''), request.get('registry_token', '')
        if not isinstance(user, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', user):
            raise ValueError('invalid registry user')
        if not isinstance(token, str) or not 10 <= len(token) <= 2048 or '\n' in token:
            raise ValueError('invalid registry credential')
    if set(request) - allowed:
        raise ValueError('fields not allowed for action')
    return action


def compose(root, *args):
    project = 'opentodo' if root == PROD else 'opentodo-test'
    return run('docker', 'compose', '-p', project, '-f', str(root / 'docker-compose.yml'), *args)


def config(root):
    return json.loads(compose(root, 'config', '--format', 'json'))


def current(root):
    return config(root)['services']['opentodo']['image']


def set_image(root, image):
    value = config(root)
    value['services']['opentodo']['image'] = image
    write_json(root / 'docker-compose.yml', value)
    sync_portainer(root / 'docker-compose.yml', 'opentodo' if root == PROD else 'opentodo-test')


def sync_portainer(source, container='opentodo'):
    # Portainer stores the stack's source here; keep its next redeploy consistent.
    # Discover the stack by its existing container_name, never modify other stacks.
    matches = []
    for path in Path('/opt/portainer/data/compose').glob('*/docker-compose.yml'):
        text = path.read_text()
        if re.search(r'container_name["\s]*:["\s]*' + re.escape(container) + r'["\s,\n}]', text):
            matches.append(path)
    if len(matches) != 1:
        raise RuntimeError('expected exactly one managed production Portainer stack')
    matches[0].write_text(source.read_text())


def healthy(container, tries=60):
    for _ in range(tries):
        try:
            run('docker', 'exec', container, '/opentodo', 'healthcheck', timeout=10)
            return
        except (RuntimeError, subprocess.TimeoutExpired):
            time.sleep(1)
    raise RuntimeError(f'{container} did not become healthy')


def maintenance(enabled):
    old = SNIPPET.read_text()
    SNIPPET.write_text('header X-OpenTodo-Maintenance true\nrespond "OpenTodo update in progress. Please retry shortly." 503\n'
                       if enabled else 'header -X-OpenTodo-Maintenance\n')
    try:
        run('caddy', 'validate', '--config', '/etc/caddy/Caddyfile')
        run('systemctl', 'reload', 'caddy')
    except Exception:
        SNIPPET.write_text(old)
        raise


def backup_db(source, target):
    with closing(sqlite3.connect(f'file:{source}?mode=ro', uri=True, timeout=30)) as src:
        with closing(sqlite3.connect(target)) as dst:
            src.backup(dst)
            if dst.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuntimeError('database integrity check failed')


def generation(db):
    with closing(sqlite3.connect(f'file:{db}?mode=ro', uri=True)) as con:
        return con.execute("SELECT value FROM settings WHERE key='generation'").fetchone()[0]


def native_archive(db, archive, version):
    with closing(sqlite3.connect(f'file:{db}?mode=ro', uri=True)) as con:
        schema = con.execute('PRAGMA user_version').fetchone()[0]
    with db.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest = {'format': 'opentodo-backup', 'formatVersion': 1, 'appVersion': version,
                'schemaVersion': schema, 'createdAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'generation': generation(db), 'compression': 'gzip', 'encrypted': False,
                'files': [{'name': 'opentodo.db', 'size': db.stat().st_size, 'sha256': digest}]}
    content = json.dumps(manifest).encode()
    with tarfile.open(archive, 'w:gz') as tar:
        info = tarfile.TarInfo('manifest.json')
        info.size = len(content)
        tar.addfile(info, io.BytesIO(content))
        tar.add(db, arcname='opentodo.db')
    archive.chmod(0o644)  # Parent directory remains root-only; restore container runs as nonroot.


def own_data(data):
    for path in [data, *data.rglob('*')]:
        if path.is_symlink():
            raise RuntimeError('unexpected symlink in application data')
        os.chown(path, 65532, 65532)


def space_check():
    size = sum(p.stat().st_size for p in (PROD / 'data').rglob('*') if p.is_file())
    if shutil.disk_usage(PROD).free < max(size * 4, 768 * 1024**2):
        raise RuntimeError('insufficient disk headroom for deployment and recovery')


def rehearsal(image):
    space_check()
    with tempfile.TemporaryDirectory(prefix='migration-', dir=STATE) as temp:
        data = Path(temp) / 'data'
        data.mkdir(mode=0o700)
        backup_db(PROD / 'data/opentodo.db', data / 'opentodo.db')
        own_data(data)
        try:
            run('docker', 'run', '-d', '--name', 'opentodo-migration-check', '--network', 'none',
                '--memory', '192m', '-v', f'{data}:/data', image)
            healthy('opentodo-migration-check')
        finally:
            run('docker', 'rm', '-f', 'opentodo-migration-check')


def pull(request):
    with tempfile.TemporaryDirectory(prefix='registry-', dir=STATE) as temp:
        env = dict(os.environ, DOCKER_CONFIG=temp)
        run('docker', 'login', 'ghcr.io', '-u', request['registry_user'], '--password-stdin',
            input=request['registry_token'] + '\n', env=env)
        run('docker', 'pull', request['image'], env=env, timeout=600)
    revision = run('docker', 'inspect', request['image'], '--format',
                   '{{index .Config.Labels "org.opencontainers.image.revision"}}')
    if revision != request['revision']:
        raise RuntimeError('image revision differs from requested source commit')


def stage(request):
    (STATE / 'staged.json').unlink(missing_ok=True)
    pull(request)
    baseline = current(PROD)
    rehearsal(request['image'])
    set_image(TEST, request['image'])
    compose(TEST, 'up', '-d', '--pull', 'never')
    healthy('opentodo-test')
    write_json(STATE / 'staged.json', {k: request[k] for k in ('image', 'revision')} | {'baseline': baseline})
    return {'status': 'staged', 'image': request['image'], 'revision': request['revision']}


def snapshot():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    target = BACKUPS / stamp
    target.mkdir(mode=0o700)
    image = current(PROD)
    shutil.copy2(PROD / 'docker-compose.yml', target / 'compose.json')
    with tarfile.open(target / 'data.tar.gz', 'w:gz') as tar:
        tar.add(PROD / 'data', arcname='data')
    backup_db(PROD / 'data/opentodo.db', target / 'opentodo.db')
    version = run('docker', 'run', '--rm', '--network', 'none', image, 'version')
    native_archive(target / 'opentodo.db', target / 'restore.tar.gz', version)
    write_json(target / 'metadata.json', {'image': image, 'created': stamp})
    return target


def restore(target):
    # This path comes exclusively from root-owned state, never from an SSH request.
    if target.parent != BACKUPS or not target.is_dir() or target.is_symlink():
        raise RuntimeError('invalid recovery snapshot')
    image = read_json(target / 'metadata.json')['image']
    compose(PROD, 'stop')
    displaced = target / ('displaced-data-' + str(time.time_ns()))
    (PROD / 'data').rename(displaced)
    with tarfile.open(target / 'data.tar.gz') as tar:
        tar.extractall(PROD, filter='data')
    own_data(PROD / 'data')
    old_generation = generation(PROD / 'data/opentodo.db')
    run('docker', 'run', '--rm', '--network', 'none', '-v', f'{PROD / "data"}:/data',
        '-v', f'{target / "restore.tar.gz"}:/restore.tar.gz:ro', image,
        'restore', '--data-dir', '/data', '/restore.tar.gz')
    if generation(PROD / 'data/opentodo.db') == old_generation:
        raise RuntimeError('restore failed to rotate sync generation')
    shutil.copy2(target / 'compose.json', PROD / 'docker-compose.yml')
    sync_portainer(PROD / 'docker-compose.yml')
    compose(PROD, 'up', '-d', '--pull', 'never')
    healthy('opentodo')


def promote(request):
    staged = read_json(STATE / 'staged.json')
    if any(staged[k] != request[k] for k in ('image', 'revision')):
        raise RuntimeError('requested image was not successfully staged')
    if current(TEST) != request['image'] or current(PROD) != staged['baseline']:
        raise RuntimeError('staging or production baseline changed; stage again')
    healthy('opentodo-test', tries=1)
    space_check()
    maintenance(True)
    target = None
    try:
        write_json(STATE / 'pending.json', {'snapshot': None, 'phase': 'snapshot'})
        compose(PROD, 'stop')
        target = snapshot()
        write_json(STATE / 'pending.json', {'snapshot': str(target)})
        set_image(PROD, request['image'])
        compose(PROD, 'up', '-d', '--pull', 'never')
        healthy('opentodo')
    except Exception:
        if target is not None:
            restore(target)
        else:
            compose(PROD, 'up', '-d', '--pull', 'never')
            healthy('opentodo')
        maintenance(False)
        (STATE / 'pending.json').unlink(missing_ok=True)
        raise
    write_json(STATE / 'previous.json', {'snapshot': str(target), 'deployed': request['image']})
    maintenance(False)
    (STATE / 'pending.json').unlink(missing_ok=True)
    prune_snapshots()
    return {'status': 'promoted', 'image': request['image'], 'backup': target.name}


def prune_snapshots():
    snapshots = sorted(p for p in BACKUPS.iterdir() if re.fullmatch(r'\d{8}T\d{12}Z', p.name) and p.is_dir())
    # Displaced data is retained for deliberate operator review, never auto-pruned.
    for path in snapshots[:-3]:
        if not list(path.glob('displaced-data-*')):
            shutil.rmtree(path)


def rollback():
    previous = read_json(STATE / 'previous.json')
    if current(PROD) != previous['deployed']:
        raise RuntimeError('production changed since the recorded deployment; operator recovery required')
    space_check()
    write_json(STATE / 'pending.json', {'snapshot': previous['snapshot'], 'phase': 'rollback'})
    maintenance(True)
    restore(Path(previous['snapshot']))
    (STATE / 'staged.json').unlink(missing_ok=True)
    (STATE / 'previous.json').unlink()
    maintenance(False)
    (STATE / 'pending.json').unlink(missing_ok=True)
    return {'status': 'rolled back', 'image': current(PROD)}


def main():
    import fcntl  # Linux only; pure validation tests can run on Windows.
    os.umask(0o077)
    if os.geteuid() != 0 or len(sys.argv) > 2:
        raise ValueError('root operator helper accepts JSON stdin only')
    mode = sys.argv[1] if len(sys.argv) == 2 else 'operator'
    if mode not in ('operator', '--stage-only', '--production-only'):
        raise ValueError('invalid operator mode')
    raw = sys.stdin.buffer.read(8193)
    if len(raw) > 8192:
        raise ValueError('request too large')
    request = json.loads(raw)
    action = validate(request)
    enforce_role(action, mode)
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    BACKUPS.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (STATE / 'lock').open('w') as lock, Path('/run/lock/tabsoff-backup.lock').open('a') as backup_lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(backup_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (STATE / 'pending.json').exists() and action != 'status':
            raise RuntimeError('unfinished deployment: operator recovery required; see pending.json')
        if action == 'stage':
            result = stage(request)
        elif action == 'promote':
            result = promote(request)
        elif action == 'rollback':
            result = rollback()
        else:
            result = {'production': current(PROD), 'test': current(TEST),
                      'staged': read_json(STATE / 'staged.json') if (STATE / 'staged.json').exists() else None,
                      'pending': (STATE / 'pending.json').exists()}
        print(json.dumps(result))


def enforce_role(action, mode):
    if mode == '--stage-only' and action not in ('stage', 'status'):
        raise ValueError('staging key cannot modify production')
    if mode == '--production-only' and action not in ('promote', 'rollback', 'status'):
        raise ValueError('production key cannot select untested images')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # Exception text is deliberately sanitized by subprocess wrappers.
        print(f'Release failed: {type(exc).__name__}: {exc}', file=sys.stderr)
        sys.exit(1)
