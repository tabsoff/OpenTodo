#!/usr/bin/env python3
"""GitHub runner client: credentials travel through encrypted stdin, never argv."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import release


def prepare(status, action):
    if status['pending']:
        raise RuntimeError('Unfinished server deployment requires recovery')
    if action == 'promote':
        staged = status.get('staged')
        if not staged or staged['baseline'] != status['production'] or staged['image'] != status['test']:
            raise RuntimeError('No current tested candidate; stage again')
        release.validate({'action': 'promote', 'image': staged['image'], 'revision': staged['revision']})
        return {k: staged[k] for k in ('image', 'revision')}
    if action != 'rollback' or not status.get('previous'):
        raise RuntimeError('No recorded rollback is available')
    if status['previous']['deployed'] != status['production']:
        raise RuntimeError('Production changed since the rollback snapshot')
    return {}


def report(candidate, action):
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        for key, value in candidate.items():
            output.write(f'{key}={value}\n')
    with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as summary:
        summary.write(f'### Production request: {action}\n\n')
        if candidate:
            summary.write(f'Source: `{candidate["revision"]}`\n\nImage: `{candidate["image"]}`\n\n')
        else:
            summary.write('Restore the recorded pre-update database and paired image.\n\n')
        summary.write('Owner approval is required. Server state is checked again before changes.\n')


def main():
    action = os.environ['RELEASE_ACTION']
    request = {'action': action}
    if action == 'prepare':
        request['action'] = 'status'
    if action in ('stage', 'promote'):
        request.update(image=os.environ['RELEASE_IMAGE'], revision=os.environ['RELEASE_REVISION'])
    if action == 'stage':
        request.update(registry_user=os.environ['GITHUB_ACTOR'], registry_token=os.environ['GH_TOKEN'])
    if action == 'stage' and not request['image']:
        image = 'ghcr.io/tabsoff/opentodo:sha-' + request['revision']
        if not re.fullmatch(r'[0-9a-f]{40}', request['revision']):
            raise ValueError('invalid source revision')
        result = subprocess.check_output(['docker', 'buildx', 'imagetools', 'inspect', image,
                                          '--format', '{{json .Manifest}}'], text=True)
        digest = json.loads(result)['digest']
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', digest):
            raise ValueError('invalid registry digest')
        request['image'] = 'ghcr.io/tabsoff/opentodo@' + digest
    with tempfile.TemporaryDirectory() as temp:
        key = Path(temp) / 'key'
        key.write_text(os.environ['DEPLOY_KEY'].replace('\r\n', '\n').strip() + '\n', newline='\n')
        key.chmod(0o600)
        hosts = Path(temp) / 'known_hosts'
        hosts.write_text(os.environ['DEPLOY_KNOWN_HOSTS'].replace('\r\n', '\n').strip() + '\n', newline='\n')
        command = ['ssh', '-T', '-i', str(key), '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
                        '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=15',
                        '-o', f'UserKnownHostsFile={hosts}', 'opentodo-deploy@89.223.70.53']
        def call(value):
            result = subprocess.run(command, input=json.dumps(value), text=True, check=True,
                                    stdout=subprocess.PIPE, timeout=1200)
            return json.loads(result.stdout)
        status = call({'action': 'status'})
        if status.get('helper_sha256') != release.helper_checksum():
            raise RuntimeError('Server helper differs from this controller; install the reviewed helper first')
        if action == 'prepare':
            report(prepare(status, os.environ['PRODUCTION_ACTION']), os.environ['PRODUCTION_ACTION'])
        else:
            release.validate(request)
            print(json.dumps(call(request)))


if __name__ == '__main__':
    main()
