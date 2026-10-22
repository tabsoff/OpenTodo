#!/usr/bin/env python3
"""Propose upstream release commits; do not reset the downstream branch."""
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def push_update(branch):
    # GITHUB_TOKEN cannot write changed workflow files. A deploy key is limited
    # to this repository and cannot access the VPS or other repositories.
    if not re.fullmatch(r'upstream/v\d+\.\d+\.\d+', branch):
        raise ValueError('invalid update branch')
    with tempfile.TemporaryDirectory() as temp:
        key, hosts = Path(temp) / 'key', Path(temp) / 'known_hosts'
        key.write_text(os.environ['UPSTREAM_PUSH_KEY'] + '\n')
        key.chmod(0o600)
        hosts.write_text(os.environ['UPSTREAM_KNOWN_HOSTS'] + '\n')
        command = ' '.join(shlex.quote(v) for v in [
            'ssh', '-i', str(key), '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
            '-o', 'StrictHostKeyChecking=yes', '-o', f'UserKnownHostsFile={hosts}',
            '-o', 'ConnectTimeout=15'])
        subprocess.run(['git', 'push', 'git@github.com:tabsoff/OpenTodo.git', 'HEAD:refs/heads/' + branch],
                       env=dict(os.environ, GIT_SSH_COMMAND=command), check=True, timeout=120)


def main():
    release = json.loads(run('gh', 'api', 'repos/pixari/OpenTodo/releases/latest'))
    tag = release['tag_name']
    if release['draft'] or release['prerelease'] or not re.fullmatch(r'v\d+\.\d+\.\d+', tag):
        raise ValueError('expected stable semantic release')
    run('git', 'fetch', 'https://github.com/pixari/OpenTodo.git', 'refs/tags/' + tag)
    commit = run('git', 'rev-parse', 'FETCH_HEAD^{commit}')
    if subprocess.run(['git', 'merge-base', '--is-ancestor', commit, 'HEAD']).returncode == 0:
        print(tag + ' is already included')
        return
    branch = 'upstream/' + tag
    existing = json.loads(run('gh', 'pr', 'list', '--repo', 'tabsoff/OpenTodo', '--state', 'all',
                              '--base', 'tabsoff', '--head', branch, '--json', 'url'))
    if existing:
        print(existing[0]['url'])
        return
    run('git', 'config', 'user.name', 'github-actions[bot]')
    run('git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    run('git', 'checkout', '-b', branch)
    merge = subprocess.run(['git', 'merge', '--no-ff', '--no-edit', commit], capture_output=True)
    clean = merge.returncode == 0
    if not clean:
        run('git', 'merge', '--abort')
        # A release-only head exposes the conflict in GitHub without discarding custom work.
        run('git', 'checkout', '--detach', commit)
    # No --force and no release tag push.
    push_update(branch)
    body = Path('upstream-update-body.md')
    body.write_text(f'Integrate official OpenTodo {tag} into the downstream branch.\n\n'
                    f'Official release: {release["html_url"]}\n\n'
                    'Review conflicts and all CI checks, merge, then verify staging before manually promoting. '
                    'This PR never deploys production automatically.\n' +
                    ('\nConflicts require manual resolution before CI can run.\n' if not clean else ''))
    print(run('gh', 'pr', 'create', '--repo', 'tabsoff/OpenTodo', '--base', 'tabsoff', '--head', branch,
              '--title', 'Update official OpenTodo to ' + tag, '--body-file', str(body)))
    if clean:
        # Bot-authored events intentionally do not launch workflows; explicit dispatch does.
        run('gh', 'workflow', 'run', 'ci.yml', '--repo', 'tabsoff/OpenTodo', '--ref', branch)


if __name__ == '__main__':
    main()
