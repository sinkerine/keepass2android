#!/usr/bin/env python3
"""Host checks for the dedicated streamed installed-APK identity gate."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import keeshare_local_acceptance as scenario

BASE = "/data/app/a'quote$(never-execute)/base.apk"
DATA = b'complete installed bytes'
DIGEST = hashlib.sha256(DATA).hexdigest()


class StreamedProvenanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.journey = scenario.LocalAcceptance.__new__(scenario.LocalAcceptance)
        self.journey.art = Path(temporary.name)
        self.journey.package = 'test'
        self.journey.adb = ['adb', '-s', 'emulator-5554']
        self.journey.provenance = {'status': 'collecting', 'transport_root_cause': 'unknown'}
        self.journey.transport_failed = False
        self.received, self.guest = DATA, DIGEST
        self.returncode, self.timeout = 0, False
        self.changed_paths = False
        self.calls = []
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, ANDROID_SERIAL='emulator-5554',
                   ADB_SERVER_SOCKET='tcp:127.0.0.1:43210').start()
        patch.object(scenario, 'EXPECTED_APK_BYTES', len(DATA)).start()
        patch.object(scenario, 'APPROVED_APK', DIGEST).start()
        patch.object(scenario.subprocess, 'run', side_effect=self.command).start()

    def command(self, argv, **kwargs):
        self.calls.append(argv)
        self.assertEqual(argv[:3], ['adb', '-s', 'emulator-5554'])
        self.assertNotIn('shell', kwargs)
        args = argv[3:]
        if args == ['shell', 'pm', 'path', 'test']:
            path = '/data/app/changed/base.apk' if self.changed_paths and len(self.calls) > 1 else BASE
            return subprocess.CompletedProcess(argv, 0, ('package:' + path + '\n').encode(), b'')
        if args == ['exec-out', 'cat', BASE]:
            self.assertEqual(kwargs['timeout'], 90)
            kwargs['stdout'].write(self.received)
            kwargs['stderr'].write(b'stream diagnostic')
            if self.timeout:
                raise subprocess.TimeoutExpired(argv, 90)
            return subprocess.CompletedProcess(argv, self.returncode)
        if args == ['shell', 'sha256sum', shlex.quote(BASE)]:
            return subprocess.CompletedProcess(argv, 0, (self.guest + '  ' + BASE + '\n').encode(), b'')
        self.fail('Unexpected command: ' + repr(argv))

    def test_complete_stream_requires_guest_hash_and_stable_paths(self):
        result = self.journey.installed_apk()
        self.assertEqual(result['sha256'], DIGEST)
        self.assertEqual(result['guest_sha256'], DIGEST)
        self.assertEqual(result['bytes'], len(DATA))
        self.assertEqual(len(self.calls), 4)
        proof = json.loads((self.journey.art / 'local-acceptance-streamed-provenance.json').read_text())
        self.assertEqual(proof['status'], 'verified')
        stream = proof['commands'][1]
        self.assertEqual(stream['stdout_bytes'], len(DATA))
        self.assertEqual(stream['stderr'], 'stream diagnostic')
        self.assertEqual(stream['returncode'], 0)
        self.assertGreaterEqual(stream['duration_seconds'], 0)
        self.assertFalse(self.journey.transport_failed)

    def test_short_stream_stops_without_retry_or_guest_acceptance(self):
        self.received = DATA[:-1]
        with self.assertRaisesRegex(RuntimeError, 'byte count mismatch'):
            self.journey.installed_apk()
        self.assertEqual(len(self.calls), 2)
        self.assertTrue(self.journey.transport_failed)
        self.assertEqual(self.journey.provenance['status'], 'failed')

    def test_same_size_wrong_received_hash_is_refused(self):
        self.received = b'x' * len(DATA)
        with self.assertRaisesRegex(RuntimeError, 'identity mismatch'):
            self.journey.installed_apk()
        self.assertEqual(self.journey.provenance['received_sha256'], hashlib.sha256(self.received).hexdigest())

    def test_guest_mismatch_is_refused(self):
        self.guest = '0' * 64
        with self.assertRaisesRegex(RuntimeError, 'identity mismatch'):
            self.journey.installed_apk()

    def test_changed_paths_are_refused(self):
        self.changed_paths = True
        with self.assertRaisesRegex(RuntimeError, 'paths changed'):
            self.journey.installed_apk()

    def test_stream_nonzero_exit_stops_without_retry(self):
        self.returncode = 1
        with self.assertRaises(subprocess.CalledProcessError):
            self.journey.installed_apk()
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.journey.provenance['commands'][1]['returncode'], 1)

    def test_timeout_preserves_partial_bytes_and_stops_without_retry(self):
        self.received = DATA[:3]
        self.timeout = True
        with self.assertRaises(subprocess.TimeoutExpired):
            self.journey.installed_apk()
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.journey.provenance['received_bytes'], 3)
        self.assertEqual(self.journey.provenance['commands'][1]['error'], 'timeout')
        self.assertTrue(self.journey.transport_failed)


if __name__ == '__main__':
    unittest.main()
