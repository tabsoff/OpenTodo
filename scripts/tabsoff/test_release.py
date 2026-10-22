import hashlib
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('release', Path(__file__).with_name('release.py'))
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
IMAGE = 'ghcr.io/tabsoff/opentodo@sha256:' + 'a' * 64
REV = 'b' * 40


class ReleaseTests(unittest.TestCase):
    def test_staging_key_cannot_promote_or_rollback(self):
        for action in ('promote', 'rollback'):
            with self.assertRaises(ValueError):
                release.enforce_role(action, '--stage-only')
        with self.assertRaises(ValueError):
            release.enforce_role('stage', '--production-only')
        release.enforce_role('status', '--stage-only')

    def test_rejects_arbitrary_images_actions_and_credential_smuggling(self):
        invalid = [
            {'action': 'shell'}, {'action': 'rollback', 'image': IMAGE},
            {'action': 'promote', 'image': IMAGE, 'revision': REV, 'registry_token': 'secret'},
            {'action': 'promote', 'image': 'ghcr.io/tabsoff/opentodo:latest', 'revision': REV},
            {'action': 'promote', 'image': IMAGE + '\n', 'revision': REV},
            {'action': 'promote', 'image': IMAGE.replace('tabsoff', 'attacker'), 'revision': REV},
            {'action': 'promote', 'image': IMAGE, 'revision': 'main;touch /tmp/owned'},
            {'action': 'status', 'command': 'id'}, [], None,
        ]
        for request in invalid:
            with self.subTest(request=request), self.assertRaises(ValueError):
                release.validate(request)

    def test_allowed_requests(self):
        for action in ('status', 'rollback'):
            self.assertEqual(release.validate({'action': action}), action)
        request = {'action': 'promote', 'image': IMAGE, 'revision': REV}
        self.assertEqual(release.validate(request), 'promote')
        self.assertEqual(release.validate(request | {'action': 'stage', 'registry_user': 'tabsoff',
                                                     'registry_token': 'x' * 40}), 'stage')

    def test_backup_is_consistent_and_native_archive_verifies_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            db = root / 'live.db'
            with closing(sqlite3.connect(db)) as con:
                con.execute('PRAGMA journal_mode=WAL')
                con.execute('PRAGMA user_version=123')
                con.execute('CREATE TABLE settings (key TEXT, value TEXT)')
                con.execute("INSERT INTO settings VALUES ('generation', 'old-generation')")
                con.commit()
                release.backup_db(db, root / 'backup.db')
            release.native_archive(root / 'backup.db', root / 'restore.tar.gz', 'v-test')
            with tarfile.open(root / 'restore.tar.gz') as tar:
                self.assertEqual(tar.getnames()[0], 'manifest.json')
                manifest = json.load(tar.extractfile('manifest.json'))
                content = tar.extractfile('opentodo.db').read()
            self.assertEqual(manifest['schemaVersion'], 123)
            self.assertEqual(manifest['generation'], 'old-generation')
            self.assertEqual(manifest['files'][0]['size'], len(content))
            self.assertEqual(manifest['files'][0]['sha256'], hashlib.sha256(content).hexdigest())

    def test_stale_or_unstaged_promotion_never_stops_production(self):
        request = {'action': 'promote', 'image': IMAGE, 'revision': REV}
        staged = {'image': IMAGE, 'revision': REV, 'baseline': 'old'}
        with patch.object(release, 'read_json', return_value=staged), \
                patch.object(release, 'current', side_effect=[IMAGE, 'changed']), \
                patch.object(release, 'maintenance') as maintenance:
            with self.assertRaisesRegex(RuntimeError, 'baseline changed'):
                release.promote(request)
            maintenance.assert_not_called()
        with patch.object(release, 'read_json', return_value=staged | {'revision': 'c' * 40}), \
                patch.object(release, 'maintenance') as maintenance:
            with self.assertRaisesRegex(RuntimeError, 'not successfully staged'):
                release.promote(request)
            maintenance.assert_not_called()

    def test_failed_candidate_restores_paired_snapshot_before_reopening_site(self):
        request = {'action': 'promote', 'image': IMAGE, 'revision': REV}
        staged = {'image': IMAGE, 'revision': REV, 'baseline': 'old'}
        with tempfile.TemporaryDirectory() as temp, \
                patch.object(release, 'STATE', Path(temp)), \
                patch.object(release, 'read_json', return_value=staged), \
                patch.object(release, 'current', side_effect=[IMAGE, 'old']), \
                patch.object(release, 'space_check'), \
                patch.object(release, 'compose'), \
                patch.object(release, 'set_image'), \
                patch.object(release, 'snapshot', return_value=Path(temp) / 'snapshot') as snapshot, \
                patch.object(release, 'healthy', side_effect=[None, RuntimeError('unhealthy')]), \
                patch.object(release, 'restore') as restore, \
                patch.object(release, 'maintenance') as maintenance:
            with self.assertRaisesRegex(RuntimeError, 'unhealthy'):
                release.promote(request)
            restore.assert_called_once_with(snapshot.return_value)
            self.assertEqual(maintenance.call_args_list, [unittest.mock.call(True), unittest.mock.call(False)])
            self.assertFalse((Path(temp) / 'pending.json').exists())


if __name__ == '__main__':
    unittest.main()
