#!/usr/bin/env python3
"""Operator-only synthetic restore check; never mounts production or test data."""
import importlib.util
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import urllib.request
import json

spec = importlib.util.spec_from_file_location('release', Path(__file__).with_name('release.py'))
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def main():
    image = sys.argv[1]
    with tempfile.TemporaryDirectory(prefix='opentodo-restore-smoke-') as temp:
        root = Path(temp)
        data = root / 'data'
        data.mkdir(mode=0o700)
        os.chown(data, 65532, 65532)
        try:
            release.run('docker', 'run', '-d', '--network', 'none', '--name', 'opentodo-restore-smoke',
                        '-v', f'{data}:/data', image)
            release.healthy('opentodo-restore-smoke')
            release.run('docker', 'stop', 'opentodo-restore-smoke')
            original = release.generation(data / 'opentodo.db')
            release.backup_db(data / 'opentodo.db', root / 'backup.db')
            release.native_archive(root / 'backup.db', root / 'restore.tar.gz', 'v0.9.0')
            release.run('docker', 'run', '--rm', '--network', 'none', '-v', f'{data}:/data',
                        '-v', f'{root / "restore.tar.gz"}:/restore.tar.gz:ro', image,
                        'restore', '--data-dir', '/data', '/restore.tar.gz')
            assert release.generation(data / 'opentodo.db') != original, 'sync generation did not change'
            release.run('docker', 'start', 'opentodo-restore-smoke')
            release.healthy('opentodo-restore-smoke')
            print('PASS: official restore accepts generated archive, rotates generation and restarts healthy')
        finally:
            release.run('docker', 'rm', '-f', 'opentodo-restore-smoke')


if __name__ == '__main__':
    main()
