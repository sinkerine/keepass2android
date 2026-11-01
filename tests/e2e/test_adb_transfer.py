"""Host tests for adb_transfer.pull_verified with a simulated ADB transport."""
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import adb_transfer

DATA = os.urandom(300_000)
SHA = hashlib.sha256(DATA).hexdigest()


class FakeAdb:
    """Each pull consumes one scripted outcome: 'ok', 'short-rc0', 'fail', 'corrupt', 'timeout'."""

    def __init__(self, outcomes, data=DATA, offline_polls=2, mutate_after_pull=False):
        self.outcomes = list(outcomes)
        self.data = data
        self.offline = 0
        self.offline_polls = offline_polls
        self.mutate_after_pull = mutate_after_pull
        self.pulls = 0

    def __call__(self, args, timeout):
        def done(rc=0, out=b'', err=b''):
            return subprocess.CompletedProcess(args, rc, out, err)
        if args[0] == 'get-state':
            if self.offline:
                self.offline -= 1
                return done(1, b'', b'error: device offline')
            return done(0, b'device\n')
        if args[:2] == ['shell', 'stat']:
            return done(0, f'{len(self.data)}\n'.encode())
        if args[:2] == ['shell', 'sha256sum']:
            return done(0, f'{hashlib.sha256(self.data).hexdigest()}  {args[2]}\n'.encode())
        assert args[0] == 'pull', args
        self.pulls += 1
        outcome = self.outcomes.pop(0)
        target = Path(args[2])
        if self.mutate_after_pull:
            self.data = self.data + b'x'
        if outcome == 'timeout':
            target.write_bytes(DATA[:10])
            raise subprocess.TimeoutExpired(args, timeout)
        if outcome == 'ok':
            target.write_bytes(DATA)
            return done()
        if outcome == 'corrupt':
            target.write_bytes(bytes([DATA[0] ^ 1]) + DATA[1:])
            return done()
        self.offline = self.offline_polls
        target.write_bytes(DATA[:len(DATA) // 3])
        return done(0 if outcome == 'short-rc0' else 1, b'', b'adb: error: failed to read copy response')


class PullVerifiedTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.local = self.dir / 'base.apk'
        self.record = self.dir / 'record.json'
        os.environ.setdefault('ANDROID_SERIAL', 'emulator-test')
        sleep = mock.patch('adb_transfer.time.sleep')
        sleep.start()
        self.addCleanup(sleep.stop)
        self.idle = mock.patch('adb_transfer.wait_until_idle', return_value=(True, 3.0, [0.9, 0.9, 0.9]))
        self.idle_wait = self.idle.start()
        self.addCleanup(self.idle.stop)

    def pull(self, fake, **kwargs):
        with mock.patch('adb_transfer._run', fake):
            return adb_transfer.pull_verified('/data/app/x/base.apk', self.local,
                                              record_path=self.record, **kwargs)

    def assert_no_partial(self):
        self.assertEqual([p for p in self.dir.iterdir() if p.name.endswith('.partial')], [])

    def test_clean_transfer_is_verified(self):
        record = self.pull(FakeAdb(['ok']), expected_sha256=SHA, check=lambda: ['p'])
        self.assertEqual(record['status'], 'verified')
        self.assertEqual(record['received_sha256'], SHA)
        self.assertEqual(record['guest_sha256'], SHA)
        self.assertEqual(self.local.read_bytes(), DATA)
        self.assertEqual(json.loads(self.record.read_text())['status'], 'verified')

    def test_silent_truncation_with_exit_zero_is_retried_not_accepted(self):
        fake = FakeAdb(['short-rc0', 'ok'])
        record = self.pull(fake)
        first = record['attempts'][0]
        self.assertEqual((first['rc'], first['received']), (0, len(DATA) // 3))
        self.assertTrue(first['partial_removed'])
        self.assertIsNotNone(first['reconnect_seconds'])
        self.assertEqual(record['status'], 'verified')
        self.assertEqual(self.local.read_bytes(), DATA)
        self.assertEqual(fake.pulls, 2)

    def test_disconnect_reconnect_then_success(self):
        record = self.pull(FakeAdb(['fail', 'ok'], offline_polls=3))
        self.assertEqual([a['rc'] for a in record['attempts']], [1, 0])
        self.assertEqual(record['status'], 'verified')
        # A reconnect alone is not enough: the retry waits for an idle guest.
        self.assertEqual(self.idle_wait.call_count, 1)
        self.assertEqual(record['attempts'][0]['idle_samples'], [0.9, 0.9, 0.9])

    def test_busy_guest_after_failure_stops_retrying(self):
        self.idle_wait.return_value = (False, 90.0, [0.0, 0.1])
        fake = FakeAdb(['fail', 'ok'])
        with self.assertRaises(adb_transfer.TransferError) as caught:
            self.pull(fake)
        self.assertIn('stayed busy', str(caught.exception))
        self.assertEqual(fake.pulls, 1)
        self.assert_no_partial()

    def test_retries_are_bounded_and_partial_removed(self):
        fake = FakeAdb(['fail', 'short-rc0', 'timeout', 'ok'])
        with self.assertRaises(adb_transfer.TransferError) as caught:
            self.pull(fake, attempts=3)
        self.assertEqual(fake.pulls, 3)
        self.assertEqual(caught.exception.record['status'], 'failed')
        self.assertFalse(self.local.exists())
        self.assert_no_partial()
        self.assertEqual(json.loads(self.record.read_text())['status'], 'failed')

    def test_full_size_wrong_hash_is_refused_without_retry(self):
        fake = FakeAdb(['corrupt', 'ok'])
        with self.assertRaises(adb_transfer.TransferError) as caught:
            self.pull(fake)
        self.assertEqual(caught.exception.record['status'], 'refused')
        self.assertEqual(fake.pulls, 1)
        self.assertFalse(self.local.exists())
        self.assert_no_partial()

    def test_expected_hash_mismatch_is_refused_before_transfer(self):
        fake = FakeAdb(['ok'])
        with self.assertRaises(adb_transfer.TransferError):
            self.pull(fake, expected_sha256='0' * 64)
        self.assertEqual(fake.pulls, 0)

    def test_changed_path_is_refused(self):
        paths = iter([['package:/a/base.apk'], ['package:/b/base.apk']])
        with self.assertRaises(adb_transfer.TransferError) as caught:
            self.pull(FakeAdb(['ok']), check=lambda: next(paths))
        self.assertIn('check changed', str(caught.exception))
        self.assertFalse(self.local.exists())
        self.assert_no_partial()

    def test_guest_file_changing_is_refused(self):
        with self.assertRaises(adb_transfer.TransferError) as caught:
            self.pull(FakeAdb(['fail', 'ok'], mutate_after_pull=True))
        self.assertIn('Guest file changed', str(caught.exception))

    def test_device_never_returns(self):
        with mock.patch('adb_transfer.time.monotonic', side_effect=itertools.count(0, 100)):
            with self.assertRaises(adb_transfer.TransferError) as caught:
                self.pull(FakeAdb(['fail'], offline_polls=10**6), reconnect_limit=1)
        self.assertIn('did not reconnect', str(caught.exception))
        self.assert_no_partial()

    def test_stale_local_file_is_removed_first(self):
        self.local.write_bytes(DATA)
        with self.assertRaises(adb_transfer.TransferError):
            self.pull(FakeAdb(['fail'] * 3))
        self.assertFalse(self.local.exists())


class WaitUntilIdleTest(unittest.TestCase):
    @staticmethod
    def stat(idle, total):
        return subprocess.CompletedProcess([], 0, f'cpu  {total - idle} 0 0 {idle} 0 0 0\n', '')

    def test_settles_after_consecutive_idle_samples(self):
        # Cumulative counters: busy, busy, then three idle intervals.
        lines = [self.stat(0, 0), self.stat(10, 100), self.stat(20, 200), self.stat(110, 300),
                 self.stat(200, 400), self.stat(290, 500)]
        with mock.patch('adb_transfer.subprocess.run', side_effect=lines), \
                mock.patch('adb_transfer.time.sleep'):
            settled, _, samples = adb_transfer.wait_until_idle(['adb'], 60)
        self.assertTrue(settled)
        self.assertEqual(samples, [0.1, 0.1, 0.9, 0.9, 0.9])

    def test_offline_device_breaks_the_streak_and_times_out(self):
        offline = subprocess.CompletedProcess([], 1, '', 'error: device offline')
        lines = [self.stat(0, 0), self.stat(90, 100), offline, self.stat(180, 200)] + [offline] * 10
        with mock.patch('adb_transfer.subprocess.run', side_effect=lines), \
                mock.patch('adb_transfer.time.sleep'), \
                mock.patch('adb_transfer.time.monotonic', side_effect=itertools.count(0, 5)):
            settled, _, samples = adb_transfer.wait_until_idle(['adb'], 60)
        self.assertFalse(settled)
        self.assertEqual(samples, [0.9])


if __name__ == '__main__':
    unittest.main()
