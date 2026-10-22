import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('upstream', Path(__file__).with_name('upstream.py'))
upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstream)


class UpstreamTransportTests(unittest.TestCase):
    def test_only_release_branches_can_be_pushed(self):
        for branch in ('tabsoff', 'main', 'upstream/v1.0.0;echo owned', 'upstream/v1.0.0\n'):
            with self.subTest(branch=branch), \
                    patch.object(upstream.subprocess, 'run') as process:
                with self.assertRaises(ValueError):
                    upstream.push_update(branch)
                process.assert_not_called()

    def test_push_uses_repo_only_ssh_with_verified_host_and_erases_private_key(self):
        files = []
        def capture(args, *, env, check, timeout):
            self.assertEqual(args, ['git', 'push', 'git@github.com:tabsoff/OpenTodo.git',
                                    'HEAD:refs/heads/upstream/v1.0.0'])
            self.assertIn('StrictHostKeyChecking=yes', env['GIT_SSH_COMMAND'])
            self.assertIn('IdentitiesOnly=yes', env['GIT_SSH_COMMAND'])
            self.assertNotIn('PRIVATE-KEY-CONTENT', env['GIT_SSH_COMMAND'])
            self.assertNotIn('--force', args)
            # Capture files directly from the dedicated temp directory below.
            files.extend(Path(temp_root).rglob('key'))
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].read_text(), 'PRIVATE-KEY-CONTENT\n')
            if os.name == 'posix':
                self.assertEqual(files[0].stat().st_mode & 0o777, 0o600)
        with tempfile.TemporaryDirectory() as temp_root, \
                patch.dict(os.environ, {'UPSTREAM_PUSH_KEY': 'PRIVATE-KEY-CONTENT',
                                        'UPSTREAM_KNOWN_HOSTS': 'github.com ssh-ed25519 host-key'}), \
                patch.object(upstream.tempfile, 'tempdir', temp_root), \
                patch.object(upstream.subprocess, 'run', side_effect=capture):
            upstream.push_update('upstream/v1.0.0')
            self.assertFalse(files[0].exists())


if __name__ == '__main__':
    unittest.main()
