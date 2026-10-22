#!/usr/bin/env python3
"""GitHub runner client: credentials travel through encrypted stdin, never argv."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


def main():
    action = os.environ['RELEASE_ACTION']
    request = {'action': action}
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
        key.write_text(os.environ['DEPLOY_KEY'] + '\n')
        key.chmod(0o600)
        hosts = Path(temp) / 'known_hosts'
        hosts.write_text(os.environ['DEPLOY_KNOWN_HOSTS'] + '\n')
        subprocess.run(['ssh', '-T', '-i', str(key), '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
                        '-o', 'StrictHostKeyChecking=yes', '-o', 'ConnectTimeout=15',
                        '-o', f'UserKnownHostsFile={hosts}', 'opentodo-deploy@89.223.70.53'],
                       input=json.dumps(request), text=True, check=True, timeout=1200)


if __name__ == '__main__':
    main()
