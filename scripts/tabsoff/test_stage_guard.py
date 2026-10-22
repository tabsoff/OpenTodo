import io
import json
import os
from pathlib import Path
import textwrap
import unittest
from unittest.mock import patch

workflow = (Path(__file__).parents[2] / '.github/workflows/tabsoff-stage-retry.yml').read_text()
guard = workflow.split("python3 - <<'PY'\n", 1)[1].split('\n          PY', 1)[0]
guard = compile(textwrap.dedent(guard), 'staging-ci-guard', 'exec')
REV = 'a' * 40
GOOD = {'head_sha': REV, 'event': 'push', 'head_branch': 'tabsoff',
        'status': 'completed', 'conclusion': 'success'}


class StageGuardTests(unittest.TestCase):
    def execute(self, runs, revision=REV):
        response = io.BytesIO(json.dumps({'workflow_runs': runs}).encode())
        with patch.dict(os.environ, {'RELEASE_REVISION': revision, 'GH_TOKEN': 'test-token'}), \
                patch('urllib.request.urlopen', return_value=response) as request, \
                patch('builtins.print'):
            exec(guard, {})
            return request

    def test_accepts_only_successful_ci_for_exact_main_branch_source(self):
        self.execute([GOOD])
        for changed in ({'event': 'pull_request'}, {'head_branch': 'feature'},
                        {'head_sha': 'b' * 40}, {'status': 'in_progress'}, {'conclusion': 'failure'}):
            with self.subTest(changed=changed), self.assertRaises(SystemExit):
                self.execute([GOOD | changed])

    def test_missing_successful_ci_is_rejected(self):
        with self.assertRaises(SystemExit):
            self.execute([])

    def test_invalid_revision_is_rejected_before_network_access(self):
        with patch('urllib.request.urlopen') as request, self.assertRaises(SystemExit):
            self.execute([], 'main;echo unsafe')
        request.assert_not_called()

    def test_api_failure_does_not_authorize_deployment(self):
        with patch.dict(os.environ, {'RELEASE_REVISION': REV, 'GH_TOKEN': 'test-token'}), \
                patch('urllib.request.urlopen', side_effect=OSError('unavailable')), \
                self.assertRaises(OSError):
            exec(guard, {})


if __name__ == '__main__':
    unittest.main()
