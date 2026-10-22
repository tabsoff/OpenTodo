#!/usr/bin/env python3
"""Root-only installation from a reviewed checkout; never invoked by CI SSH keys."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile


def install(source, target, state):
    content = source.read_bytes().replace(b'\r\n', b'\n')
    compile(content, str(source), 'exec')
    digest = hashlib.sha256(content).hexdigest()
    if target.exists() and target.read_bytes() == content:
        return digest
    if target.exists():
        shutil.copy2(target, target.with_name(target.name + '.previous'))
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temp:
        pending = Path(temp.name)
        temp.write(content)
    try:
        pending.chmod(0o755)
        pending.replace(target)
    finally:
        pending.unlink(missing_ok=True)
    (state / 'helper-install.json').write_text(json.dumps({'sha256': digest}) + '\n')
    return digest


def main():
    if os.geteuid() != 0 or len(sys.argv) != 1:
        raise ValueError('Run as root from the reviewed scripts/tabsoff directory; no arguments accepted')
    # Import the reviewed code for its lock primitive, without running its entry point.
    import release
    os.umask(0o077)
    state = release.STATE
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (state / 'lock').open('a') as lock, Path('/run/lock/tabsoff-backup.lock').open('a') as backup:
        release.lock_wait(lock)
        release.lock_wait(backup)
        if (state / 'pending.json').exists():
            raise RuntimeError('Recover the unfinished deployment before updating its helper')
        digest = install(Path(__file__).with_name('release.py'),
                         Path('/usr/local/sbin/opentodo-release'), state)
    print('Installed helper SHA256: ' + digest)


if __name__ == '__main__':
    main()
