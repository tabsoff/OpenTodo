#!/usr/bin/env python3
"""Only an exact trusted push that actually published an image can be staged."""
import json
import os
import re
import urllib.request

API = 'https://api.github.com/repos/tabsoff/OpenTodo/actions/'


def get(path):
    request = urllib.request.Request(API + path, headers={
        'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
        'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def verified(revision):
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Expected a full commit SHA')
    runs = get('workflows/ci.yml/runs?event=push&branch=tabsoff&head_sha=' +
               revision + '&per_page=100')['workflow_runs']
    for run in runs:
        if not (run['head_sha'] == revision and run['event'] == 'push' and
                run['head_branch'] == 'tabsoff' and run['status'] == 'completed' and
                run['conclusion'] == 'success' and
                run['head_repository']['full_name'] == 'tabsoff/OpenTodo'):
            continue
        page = 1
        while True:
            jobs = get(f'runs/{run["id"]}/jobs?filter=latest&per_page=100&page={page}')['jobs']
            if any(j['name'] == 'Docker image (publish, sign)' and
                   j['conclusion'] == 'success' for j in jobs):
                return True
            if len(jobs) < 100:
                break
            page += 1
    return False


def main():
    ok = verified(os.environ['RELEASE_REVISION'])
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        output.write(f'ready={str(ok).lower()}\n')
    if not ok and os.environ.get('REQUIRE_IMAGE') == 'true':
        raise RuntimeError('This revision has no successful trusted CI image publication')
    print('Verified published candidate' if ok else 'No published application image; staging skipped')


if __name__ == '__main__':
    main()
