#!/usr/bin/env python3
"""Conservative downstream CI selection; missing history always means full CI."""
import os
import re
import subprocess


def classify(files, full=False):
    code = docs = full
    for path in files:
        if path.startswith(('scripts/tabsoff/', 'openspec/changes/tabsoff-',
                            'openspec/changes/streamline-tabsoff-')):
            continue
        if path.startswith(('docs/', 'website/', 'openspec/')) or path in (
                'README.md', 'CHANGELOG.md', 'web/src/generated/help.json'):
            docs = True
        else:
            # Includes workflow edits, dependency files and future unknown inputs.
            code = docs = True
    return {'code': str(code).lower(), 'docs': str(docs).lower()}


def git(*args):
    return subprocess.check_output(['git', *args], text=True)


def profile():
    event = os.environ.get('EVENT', '')
    if (event not in ('push', 'pull_request') or
            os.environ.get('REF', '').startswith('refs/tags/') or
            os.environ.get('HEAD_REF', '').startswith('upstream/')):
        return classify([], full=True)
    base = os.environ.get('BASE' if event == 'pull_request' else 'BEFORE', '')
    if not re.fullmatch(r'[0-9a-f]{40}', base) or base == '0' * 40:
        return classify([], full=True)
    try:
        span = base + ('...HEAD' if event == 'pull_request' else '..HEAD')
        files = git('diff', '--name-only', '-z', span).split('\0')
        # Merge commits from the official-update PR retain this branch name.
        integrated = bool(re.search(r'upstream/v\d+\.\d+\.\d+',
                                    git('log', '--format=%B', base + '..HEAD')))
        return classify([p for p in files if p], full=integrated)
    except subprocess.CalledProcessError:
        return classify([], full=True)


if __name__ == '__main__':
    for key, value in profile().items():
        print(f'{key}={value}')
