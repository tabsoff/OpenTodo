#!/usr/bin/env python3
"""Real Docker release/recovery on disposable synthetic data; run as root on Linux."""
import http.cookiejar
import json
import os
from pathlib import Path
import tempfile
import sys
import urllib.request
import uuid
import release

BASE = 'ghcr.io/pixari/opentodo@sha256:416833792b4414c0604cd7bbb5011bb3ca8e261d534b38434551f45083b71064'


class API:
    def __init__(self, port):
        self.base = f'http://127.0.0.1:{port}'
        self.http = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, path, body=None):
        request = urllib.request.Request(self.base + '/api/v1/' + path,
                                        data=json.dumps(body).encode() if body is not None else None,
                                        headers={'Content-Type': 'application/json'})
        with self.http.open(request, timeout=20) as response:
            return json.load(response)

    def login(self):
        self.call('auth/login', {'email': 'release@example.test', 'password': 'synthetic-test-password-123'})

    def titles(self):
        return {t['title'] for t in self.call('tasks')['tasks']}


def main():
    if os.geteuid() != 0:
        raise RuntimeError('Disposable lifecycle test requires root for native data ownership')
    prefix = 'ot-lifecycle-' + uuid.uuid4().hex[:10]
    original_healthy = release.healthy
    candidate = prefix + ':candidate'
    projects = []
    with tempfile.TemporaryDirectory(prefix=prefix + '-') as temp:
        root = Path(temp)
        release.PROD, release.TEST = root / 'prod', root / 'test'
        release.STATE, release.BACKUPS = root / 'state', root / 'backups'
        release.MIGRATION_CONTAINER = prefix + '-migration'
        for directory in (release.STATE, release.BACKUPS):
            directory.mkdir(mode=0o700)
        names = {'opentodo': prefix + '-prod', 'opentodo-test': prefix + '-test'}
        failure = {'armed': False}
        maintenance_states = []

        def compose(directory, *args):
            project = prefix + ('-prod' if directory == release.PROD else '-test')
            command = ['docker', 'compose', '-p', project, '-f', str(directory / 'docker-compose.yml')]
            if failure['armed'] and directory == release.PROD and args[:1] == ('up',):
                failure['armed'] = False
                override = root / 'failed-candidate.json'
                override.write_text(json.dumps({'services': {'opentodo': {'entrypoint': ['/opentodo', 'version']}}}))
                command += ['-f', str(override)]
            return release.run(*command, *args)

        def healthy(container, tries=60):
            return original_healthy(names.get(container, container), tries=min(tries, 8))

        # Only host-specific plumbing and registry transport are substituted.
        # Snapshot, Compose, promotion, native restore and SQLite logic stay real.
        release.compose, release.healthy = compose, healthy
        release.maintenance = maintenance_states.append
        release.sync_portainer = lambda *args: None
        release.pull = lambda request: None
        release.housekeeping = lambda: {'synthetic': True}  # Never prune host images in a test.
        try:
            release.run('docker', 'pull', BASE, timeout=300)
            dockerfile = root / 'Dockerfile'
            source = sys.argv[1] if len(sys.argv) == 2 and sys.argv[1] else BASE
            if any(c.isspace() for c in source):
                raise ValueError('invalid candidate image')
            dockerfile.write_text(f'FROM {source}\nLABEL tabsoff.lifecycle="{prefix}"\n')
            release.run('docker', 'build', '-t', candidate, str(root), timeout=180)
            for directory, suffix in ((release.PROD, 'prod'), (release.TEST, 'test')):
                data = directory / 'data'
                data.mkdir(parents=True, mode=0o700)
                os.chown(data, 65532, 65532)
                service = {'image': BASE, 'container_name': prefix + '-' + suffix,
                           'network_mode': 'bridge', 'mem_limit': '192m',
                           'ports': ['127.0.0.1::8080'], 'volumes': [f'{data}:/data'],
                           'environment': {'OPENTODO_SETUP_TOKEN': 'synthetic-setup-token-123456'}}
                (directory / 'docker-compose.yml').write_text(json.dumps({'services': {'opentodo': service}}))
                projects.append(directory)
                compose(directory, 'up', '-d', '--pull', 'never')
                healthy('opentodo' if suffix == 'prod' else 'opentodo-test')
            port = json.loads(compose(release.PROD, 'ps', '--format', 'json'))['Publishers'][0]['PublishedPort']
            api = API(port)
            api.call('auth/register', {'email': 'release@example.test', 'name': 'Synthetic owner',
                                      'password': 'synthetic-test-password-123',
                                      'setupToken': 'synthetic-setup-token-123456'})
            api.call('tasks', {'title': 'Must survive release and recovery'})
            sentinel = release.PROD / 'data' / 'sentinel.txt'
            sentinel.write_text('paired full-data snapshot')
            generation = release.generation(release.PROD / 'data/opentodo.db')
            request = {'action': 'stage', 'image': candidate, 'revision': 'a' * 40}
            release.stage(request)
            release.promote(request | {'action': 'promote'})
            # Compose may choose another ephemeral host port after recreate.
            def reconnect():
                published = json.loads(compose(release.PROD, 'ps', '--format', 'json'))['Publishers'][0]['PublishedPort']
                session = API(published)
                session.login()
                return session
            api = reconnect()
            assert 'Must survive release and recovery' in api.titles()
            api.call('tasks', {'title': 'Added after release'})
            sentinel.write_text('changed after release')
            release.rollback()
            api = reconnect()
            assert 'Must survive release and recovery' in api.titles()
            assert 'Added after release' not in api.titles()
            assert sentinel.read_text() == 'paired full-data snapshot'
            assert release.generation(release.PROD / 'data/opentodo.db') != generation
            assert release.current(release.PROD) == BASE
            print('PASS: successful promotion, task survival, explicit paired rollback, rotated generation')

            api.call('tasks', {'title': 'Must survive failed candidate'})
            before = release.generation(release.PROD / 'data/opentodo.db')
            release.stage(request)
            failure['armed'] = True
            try:
                release.promote(request | {'action': 'promote'})
                raise AssertionError('failed candidate was accepted')
            except RuntimeError as exc:
                assert 'did not become healthy' in str(exc), str(exc)
            api = reconnect()
            assert 'Must survive failed candidate' in api.titles()
            assert release.generation(release.PROD / 'data/opentodo.db') != before
            assert release.current(release.PROD) == BASE
            assert not (release.STATE / 'pending.json').exists()
            assert maintenance_states[-2:] == [True, False]
            print('PASS: real failed container automatically restores paired image/data and reopens healthy')
        finally:
            for directory in projects:
                compose(directory, 'down', '--remove-orphans')
            release.run('docker', 'image', 'rm', candidate)


if __name__ == '__main__':
    main()
