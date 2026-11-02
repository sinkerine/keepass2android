#!/usr/bin/env python3
"""Host integration checks for the dedicated shared verified-pull identity gate."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import keeshare_local_acceptance as scenario

BASE = '/data/app/test/base.apk'
DATA = b'complete installed bytes'
DIGEST = hashlib.sha256(DATA).hexdigest()


class DedicatedInitializationTests(unittest.TestCase):
    def test_new_pin_accepted_and_historical_or_wrong_pin_rejected(self):
        def initialize(journey):
            self.assertEqual(journey.commands, [])
            self.assertFalse(journey.transport_failed)
            self.assertFalse(journey.advanced_search)
            self.assertEqual(journey.provenance['status'], 'collecting')
            journey.package = 'test'
            journey.apk = {'sha256': digest}
        for digest in (scenario.APPROVED_APK,
                       '98149d7c99a16222d02208a009e27ceaad9d1b2a851a2f609db7671577255216',
                       '0' * 64):
            with self.subTest(digest=digest), patch.object(scenario.Journey, '__init__', initialize):
                if digest == scenario.APPROVED_APK:
                    journey = scenario.LocalAcceptance()
                    self.assertEqual(journey.observations, {})
                    self.assertTrue(all(value['status'] == 'not-run' for value in journey.results.values()))
                else:
                    with self.assertRaisesRegex(AssertionError, 'dedicated approved build'):
                        scenario.LocalAcceptance()


class InstalledProvenanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.journey = scenario.LocalAcceptance.__new__(scenario.LocalAcceptance)
        self.journey.art = Path(temporary.name)
        self.journey.package = 'test'
        self.journey.provenance = {'status': 'collecting'}
        self.journey.transport_failed = False
        self.path_queries = 0
        self.changed_paths = False
        self.size = len(DATA)
        self.digest = DIGEST
        self.failure = False
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, ANDROID_SERIAL='emulator-5554',
                   ADB_SERVER_SOCKET='tcp:127.0.0.1:43210').start()
        patch.object(scenario, 'EXPECTED_APK_BYTES', len(DATA)).start()
        patch.object(scenario, 'APPROVED_APK', DIGEST).start()
        self.adb = patch.object(self.journey, 'adb_run', side_effect=self.paths).start()
        self.transfer = patch.object(scenario, 'pull_verified', side_effect=self.pull).start()

    def paths(self, *args):
        self.assertEqual(args, ('shell', 'pm', 'path', 'test'))
        self.path_queries += 1
        path = '/data/app/changed/base.apk' if self.changed_paths and self.path_queries > 1 else BASE
        return subprocess.CompletedProcess(args, 0, ('package:' + path + '\n').encode(), b'')

    def pull(self, remote, local, **kwargs):
        self.assertEqual(remote, BASE)
        self.assertEqual(kwargs['expected_sha256'], DIGEST)
        self.assertEqual(kwargs['attempts'], 3)
        self.assertEqual(kwargs['timeout'], 90)
        before = kwargs['check']()
        if self.failure:
            raise scenario.TransferError('bounded transport failure', {'status': 'failed', 'attempts': []})
        after = kwargs['check']()
        Path(local).write_bytes(DATA)
        return {'status': 'verified', 'guest_size': self.size, 'received_bytes': self.size,
                'guest_sha256': self.digest, 'received_sha256': self.digest,
                'check_before': before, 'check_after': after, 'attempts': []}

    def test_approved_identity_requires_shared_helper_and_stable_paths(self):
        apk = self.journey.installed_apk()
        self.assertEqual(apk['bytes'], len(DATA))
        self.assertEqual(apk['sha256'], DIGEST)
        self.assertEqual(apk['guest_sha256'], DIGEST)
        self.assertEqual(self.path_queries, 3)
        self.transfer.assert_called_once()
        proof = json.loads((self.journey.art / 'local-acceptance-installed-provenance.json').read_text())
        self.assertEqual(proof['status'], 'verified')
        self.assertEqual(proof['package_paths_before'], proof['package_paths_after'])

    def test_changed_path_is_refused_before_transfer(self):
        self.changed_paths = True
        with self.assertRaisesRegex(RuntimeError, 'paths changed'):
            self.journey.installed_apk()
        self.assertTrue(self.journey.transport_failed)

    def test_approved_size_is_required_in_addition_to_hash(self):
        self.size -= 1
        with self.assertRaisesRegex(RuntimeError, 'approved size'):
            self.journey.installed_apk()
        self.assertTrue(self.journey.transport_failed)

    def test_wrong_helper_identity_is_refused(self):
        self.digest = '0' * 64
        with self.assertRaisesRegex(RuntimeError, 'approved hash'):
            self.journey.installed_apk()

    def test_transfer_failure_preserves_record_without_local_retry(self):
        self.failure = True
        with self.assertRaises(scenario.TransferError):
            self.journey.installed_apk()
        self.transfer.assert_called_once()
        self.assertEqual(self.journey.provenance['transfer']['status'], 'failed')
        self.assertTrue(self.journey.transport_failed)


if __name__ == '__main__':
    unittest.main()
