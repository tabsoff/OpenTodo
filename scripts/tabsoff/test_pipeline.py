import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).parent))
import ci_profile
import client
import install
import stage_guard

REV = 'a' * 40
IMAGE = 'ghcr.io/tabsoff/opentodo@sha256:' + 'b' * 64
GOOD = {'id': 1, 'head_sha': REV, 'event': 'push', 'head_branch': 'tabsoff',
        'status': 'completed', 'conclusion': 'success',
        'head_repository': {'full_name': 'tabsoff/OpenTodo'}}


class PipelineTests(unittest.TestCase):
    def test_profiles_conserve_full_checks_for_code_and_unknown_inputs(self):
        for path in ('web/src/a.tsx', '.github/workflows/ci.yml', 'new-unknown-file'):
            self.assertEqual(ci_profile.classify([path]), {'code': 'true', 'docs': 'true'})
        for path in ('scripts/tabsoff/release.py', 'scripts/tabsoff/README.md',
                     'openspec/changes/streamline-tabsoff-pipeline/tasks.md'):
            self.assertEqual(ci_profile.classify([path]), {'code': 'false', 'docs': 'false'})
        self.assertEqual(ci_profile.classify(['docs/api.md']), {'code': 'false', 'docs': 'true'})
        self.assertEqual(ci_profile.classify(['docs/api.md'], full=True)['code'], 'true')

    def test_push_range_official_merge_and_missing_history(self):
        with patch.dict(os.environ, {'EVENT': 'push', 'BEFORE': REV, 'REF': 'refs/heads/tabsoff'}), \
                patch.object(ci_profile, 'git', side_effect=['scripts/tabsoff/client.py\0', 'routine edit']):
            self.assertEqual(ci_profile.profile()['code'], 'false')
        with patch.dict(os.environ, {'EVENT': 'push', 'BEFORE': REV}), \
                patch.object(ci_profile, 'git', side_effect=['docs/a.md\0', 'Merge upstream/v1.0.0']):
            self.assertEqual(ci_profile.profile()['code'], 'true')
        for env in ({'EVENT': 'push', 'BEFORE': '0' * 40}, {'EVENT': 'workflow_dispatch'},
                    {'EVENT': 'pull_request', 'HEAD_REF': 'upstream/v1.0.0'}):
            with patch.dict(os.environ, env, clear=True):
                self.assertEqual(ci_profile.profile()['code'], 'true')

    def check_guard(self, run=GOOD, jobs=None):
        if jobs is None:
            jobs = [{'name': 'Docker image (publish, sign)', 'conclusion': 'success'}]
        with patch.object(stage_guard, 'get', side_effect=[{'workflow_runs': [run]}, {'jobs': jobs}]):
            return stage_guard.verified(REV)

    def test_stage_requires_exact_trusted_ci_and_successful_publication(self):
        self.assertTrue(self.check_guard())
        for changed in ({'event': 'pull_request'}, {'head_branch': 'feature'},
                        {'head_sha': 'c' * 40}, {'status': 'in_progress'}, {'conclusion': 'failure'},
                        {'head_repository': {'full_name': 'attacker/OpenTodo'}}):
            with self.subTest(changed=changed):
                self.assertFalse(self.check_guard(GOOD | changed))
        self.assertFalse(self.check_guard(jobs=[{'name': 'Docker image (publish, sign)', 'conclusion': 'skipped'}]))
        with patch.object(stage_guard, 'get') as request, self.assertRaises(ValueError):
            stage_guard.verified('unsafe;input')
        request.assert_not_called()
        with patch.object(stage_guard, 'get', side_effect=OSError), self.assertRaises(OSError):
            stage_guard.verified(REV)

    def test_prepare_freezes_current_candidate_and_refuses_stale_or_pending(self):
        staged = {'image': IMAGE, 'revision': REV, 'baseline': 'old'}
        status = {'pending': False, 'production': 'old', 'test': IMAGE, 'staged': staged}
        self.assertEqual(client.prepare(status, 'promote'), {'image': IMAGE, 'revision': REV})
        for changed in ({'pending': True}, {'production': 'other'}, {'test': 'other'}, {'staged': None}):
            with self.subTest(changed=changed), self.assertRaises(RuntimeError):
                client.prepare(status | changed, 'promote')
        with self.assertRaises(RuntimeError):
            client.prepare(status, 'rollback')

    def test_installer_normalizes_content_is_idempotent_and_preserves_previous(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = root / 'source.py', root / 'installed'
            source.write_bytes(b'print(1)\r\n')
            target.write_bytes(b'previous\n')
            digest = install.install(source, target, root)
            self.assertEqual(target.read_bytes(), b'print(1)\n')
            self.assertEqual(target.with_name('installed.previous').read_bytes(), b'previous\n')
            self.assertEqual(install.install(source, target, root), digest)
            self.assertEqual(target.with_name('installed.previous').read_bytes(), b'previous\n')

    def test_client_fails_closed_on_helper_mismatch_before_any_mutation(self):
        import json
        import subprocess
        with tempfile.TemporaryDirectory() as temp, \
                patch.dict(os.environ, {'RELEASE_ACTION': 'rollback', 'DEPLOY_KEY': 'KEY\r\n',
                                        'DEPLOY_KNOWN_HOSTS': 'host ssh-ed25519 key\r\n'}), \
                patch.object(client.tempfile, 'tempdir', temp), \
                patch.object(client.subprocess, 'run', return_value=subprocess.CompletedProcess(
                    [], 0, stdout=json.dumps({'helper_sha256': 'wrong'}))) as process:
            with self.assertRaisesRegex(RuntimeError, 'differs'):
                client.main()
            self.assertEqual(json.loads(process.call_args.kwargs['input']), {'action': 'status'})
            self.assertEqual(process.call_count, 1)

    def test_manual_and_automatic_staging_share_guard_and_no_build(self):
        workflows = Path(__file__).parents[2] / '.github/workflows'
        stage = (workflows / 'tabsoff-stage.yml').read_text()
        self.assertIn('workflow_run:', stage)
        self.assertIn('workflow_dispatch:', stage)
        self.assertIn('scripts/tabsoff/stage_guard.py', stage)
        self.assertNotIn('build-push-action', stage)
        self.assertFalse((workflows / 'tabsoff-stage-retry.yml').exists())
        production = (workflows / 'tabsoff-production.yml').read_text()
        self.assertIn('needs: prepare', production)
        self.assertIn('RELEASE_IMAGE: ${{ needs.prepare.outputs.image }}', production)


if __name__ == '__main__':
    unittest.main()
