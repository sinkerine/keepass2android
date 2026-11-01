#!/usr/bin/env python3
"""Host regressions for the dedicated installed-provenance gate; no device I/O."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import keeshare_two_databases as scenario
from keeshare_journey import Journey

BASE = '/data/app/test/base.apk'
DATA = b'complete synthetic installed bytes'
DIGEST = hashlib.sha256(DATA).hexdigest()


def result(code=0, stdout=b'', stderr=b''):
    return subprocess.CompletedProcess([], code, stdout, stderr)


class InstalledProvenanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.journey = scenario.TwoDatabases.__new__(scenario.TwoDatabases)
        self.journey.art = Path(temporary.name)
        self.journey.package = 'test'
        self.journey.adb = ['adb', '-s', 'emulator-5554']
        self.journey.commands = []
        self.journey.transport_failed = False
        self.journey.provenance = {'status': 'collecting', 'commands': [],
            'recovery': {'status': 'not-needed'}, 'transport_root_cause': 'unknown'}
        self.artifact = self.journey.art / 'installed-base.apk'
        self.calls = []
        self.clock = 0
        self.path_queries = 0
        self.offline = False
        self.failed_recovery = False
        self.standard_failure = True
        self.changed_paths = False
        self.guest_digest = DIGEST
        self.received = DATA
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, ANDROID_SERIAL='emulator-5554',
                   ADB_SERVER_SOCKET='tcp:127.0.0.1:43210').start()
        patch.object(scenario, 'APPROVED_APK', DIGEST).start()
        patch.object(scenario.time, 'monotonic', side_effect=lambda: self.clock).start()
        patch.object(scenario.time, 'sleep', side_effect=self.advance).start()
        patch.object(Journey, 'adb_run', side_effect=self.adb).start()

    def advance(self, seconds):
        self.clock += seconds

    def adb(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if args == ('shell', 'pm', 'path', 'test'):
            self.path_queries += 1
            path = '/data/app/changed/base.apk' if self.changed_paths and self.path_queries > 1 else BASE
            return result(stdout=('package:' + path + '\n').encode())
        if args[0] == 'pull':
            if args[1] != '-Z' and self.standard_failure:
                self.artifact.write_bytes(b'partial bytes must be deleted')
                return result(1, stderr=b'[ 14%] transfer failed')
            if args[1] == '-Z':
                self.assertFalse(self.artifact.exists(), 'Recovery must clear partial artifact')
                if self.failed_recovery:
                    return result(1, stderr=b'error: closed')
            self.artifact.write_bytes(self.received)
            return result()
        if args == ('get-state',):
            self.assertLessEqual(kwargs['timeout'], 10)
            return result(1, stderr=b'error: device offline') if self.offline else result(stdout=b'device\n')
        if args == ('shell', 'sha256sum', BASE):
            return result(stdout=(self.guest_digest + '  ' + BASE + '\n').encode())
        self.fail('Unexpected command: ' + repr(args))

    def pulls(self):
        return [args for args, _ in self.calls if args[0] == 'pull']

    def test_recovery_receives_complete_bytes_and_retains_original_failure(self):
        apk = self.journey.installed_apk()
        self.assertEqual(apk['sha256'], DIGEST)
        self.assertEqual(apk['guest_sha256'], DIGEST)
        self.assertEqual(apk['bytes'], len(DATA))
        self.assertEqual(self.pulls(), [('pull', BASE, str(self.artifact)),
            ('pull', '-Z', BASE, str(self.artifact))])
        proof = self.journey.provenance
        self.assertEqual(proof['standard_pull']['status'], 'failed')
        failure = proof['commands'][proof['standard_pull']['command_index']]
        self.assertEqual(failure['returncode'], 1)
        self.assertIn('14%', failure['stderr'])
        self.assertEqual(proof['recovery']['status'], 'verified')
        self.assertEqual(self.path_queries, 3)
        self.assertFalse(self.journey.transport_failed)

    def test_successful_standard_pull_still_requires_independent_guest_hash(self):
        self.standard_failure = False
        self.journey.installed_apk()
        self.assertEqual(len(self.pulls()), 1)
        self.assertFalse(any(args == ('get-state',) for args, _ in self.calls))
        self.assertEqual(self.journey.provenance['recovery']['status'], 'not-needed')
        self.assertEqual(self.path_queries, 2)

    def test_offline_refused_after_ten_seconds_without_recovery_pull(self):
        self.offline = True
        with self.assertRaisesRegex(ConnectionError, 'within 10 seconds'):
            self.journey.installed_apk()
        self.assertEqual(self.clock, 10)
        self.assertEqual(len(self.pulls()), 1)
        self.assertFalse(self.artifact.exists())
        self.assertTrue(self.journey.transport_failed)
        with self.assertRaisesRegex(ConnectionError, 'no further commands'):
            self.journey.adb_run('get-state')

    def test_failed_recovery_stops_without_third_transfer(self):
        self.failed_recovery = True
        with self.assertRaises(subprocess.CalledProcessError):
            self.journey.installed_apk()
        self.assertEqual(len(self.pulls()), 2)
        self.assertEqual(self.path_queries, 2)
        self.assertEqual(self.journey.provenance['recovery']['status'], 'failed')

    def test_changed_installed_paths_refused_before_recovery(self):
        self.changed_paths = True
        with self.assertRaisesRegex(RuntimeError, 'paths changed before recovery'):
            self.journey.installed_apk()
        self.assertEqual(len(self.pulls()), 1)

    def test_full_received_bytes_and_guest_must_both_match_approved_digest(self):
        for received, guest in ((DATA + b'extra', DIGEST), (DATA, '0' * 64),
                                 (b'different build', hashlib.sha256(b'different build').hexdigest())):
            with self.subTest(received=received, guest=guest):
                self.received, self.guest_digest = received, guest
                self.calls.clear()
                self.path_queries = 0
                self.artifact.unlink(missing_ok=True)
                with self.assertRaisesRegex(RuntimeError, 'identity mismatch'):
                    self.journey.installed_apk()
                self.assertEqual(self.journey.provenance['received_sha256'],
                                 hashlib.sha256(received).hexdigest())

    def test_readiness_subprocess_timeout_stops_at_bound(self):
        original = self.adb
        def timed_out(*args, **kwargs):
            if args == ('get-state',):
                self.advance(kwargs['timeout'])
                raise subprocess.TimeoutExpired(args, kwargs['timeout'])
            return original(*args, **kwargs)
        with patch.object(Journey, 'adb_run', side_effect=timed_out):
            with self.assertRaisesRegex(ConnectionError, 'readiness timed out'):
                self.journey.installed_apk()
        self.assertEqual(self.clock, 10)
        self.assertEqual(len(self.pulls()), 1)


if __name__ == '__main__':
    unittest.main()
